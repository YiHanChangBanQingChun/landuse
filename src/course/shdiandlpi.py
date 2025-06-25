import os
import geopandas as gpd
import rasterio
import numpy as np
from shapely.geometry import box
from tqdm import tqdm

class LandscapeMetricsCalculator:
    def __init__(self, fishnet_path, raster_paths, output_dir):
        """
        初始化景观指标计算器
        :param fishnet_path: 面渔网路径（Shapefile）
        :param raster_paths: 栅格文件路径列表
        :param output_dir: 输出文件夹路径
        """
        self.fishnet_path = fishnet_path
        self.raster_paths = raster_paths
        self.output_dir = output_dir

    def _reproject_fishnet(self, fishnet_gdf, target_crs="EPSG:32649"):
        """
        将渔网重投影到目标坐标系
        :param fishnet_gdf: 渔网 GeoDataFrame
        :param target_crs: 目标坐标系（默认 EPSG:32649）
        :return: 重投影后的渔网 GeoDataFrame
        """
        if fishnet_gdf.crs != target_crs:
            fishnet_gdf = fishnet_gdf.to_crs(target_crs)
        return fishnet_gdf

    def _load_fishnet(self):
        """
        加载面渔网
        :return: GeoDataFrame
        """
        return gpd.read_file(self.fishnet_path)

    def _load_raster(self, raster_path):
        """
        加载栅格文件并重投影到 EPSG:32649
        :param raster_path: 栅格文件路径
        :return: 栅格数据数组、栅格元数据
        """
        with rasterio.open(raster_path) as src:
            # 如果栅格的坐标系不是 EPSG:32649，重投影
            if src.crs.to_string() != "EPSG:32649":
                transform, width, height = rasterio.warp.calculate_default_transform(
                    src.crs, "EPSG:32649", src.width, src.height, *src.bounds
                )
                kwargs = src.meta.copy()
                kwargs.update({
                    "crs": "EPSG:32649",
                    "transform": transform,
                    "width": width,
                    "height": height
                })

                with rasterio.open(raster_path, "r") as src_reprojected:
                    data = rasterio.warp.reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(src_reprojected, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs="EPSG:32649",
                        resampling=rasterio.enums.Resampling.nearest
                    )
            else:
                data = src.read(1)  # 读取第一波段数据
                meta = src.meta.copy()  # 复制元数据
        return data, meta

    def _calculate_shdi(self, raster_data):
        """
        计算 Shannon Diversity Index (SHDI)
        :param raster_data: 栅格数据数组
        :return: SHDI 值
        """
        # 统计每个地类的栅格数量
        unique, counts = np.unique(raster_data, return_counts=True)
        total_pixels = raster_data.size

        # 计算每个地类的比例 p_i
        proportions = counts / total_pixels

        # 计算 SHDI
        shdi = -np.sum(proportions * np.log(proportions))

        return shdi

    def _calculate_lpi(self, raster_data, total_area):
        """
        计算最大斑块指数 (LPI)
        :param raster_data: 栅格数据数组
        :param total_area: 网格总面积（栅格数量）
        :return: LPI 值
        """
        # 统计每个地类的栅格数量
        unique, counts = np.unique(raster_data, return_counts=True)

        # 找到最大斑块面积
        max_patch_area = counts.max()

        # 计算最大斑块面积占总面积的比例
        lpi = max_patch_area / total_area

        return lpi

    def _calculate_contag(self, raster_data, total_area):
        """
        计算蔓延度指数 (CONTAG)
        :param raster_data: 栅格数据数组
        :param total_area: 网格总面积（栅格数量）
        :return: CONTAG 值
        """
        # 统计每个地类的栅格数量
        unique, counts = np.unique(raster_data, return_counts=True)
        m = len(unique)  # 地类总数
    
        # 创建地类索引映射（确保地类值连续）
        class_to_index = {cls: idx for idx, cls in enumerate(unique)}
    
        # 计算每个地类的比例 P_i
        proportions = counts / total_area
    
        # 初始化邻接矩阵 g_{ik}（地类之间的边界长度）
        adjacency_matrix = np.zeros((m, m))
    
        for i in range(raster_data.shape[0]):
            for j in range(raster_data.shape[1]):
                current_class = raster_data[i, j]
                if current_class not in class_to_index:
                    continue  # 跳过无效地类
    
                current_index = class_to_index[current_class]
                neighbors = [
                    (i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)  # 上下左右
                ]
                for ni, nj in neighbors:
                    if 0 <= ni < raster_data.shape[0] and 0 <= nj < raster_data.shape[1]:
                        neighbor_class = raster_data[ni, nj]
                        if neighbor_class in class_to_index:
                            neighbor_index = class_to_index[neighbor_class]
                            adjacency_matrix[current_index, neighbor_index] += 1
    
        # 计算总邻接边界长度
        total_adjacency = np.sum(adjacency_matrix)
    
        # 计算 CONTAG
        contag = 0
        for i in range(m):
            for k in range(m):
                if total_adjacency > 0:
                    p_ik = proportions[i] * (adjacency_matrix[i, k] / total_adjacency)
                    if p_ik > 0:
                        contag += p_ik * np.log(p_ik)
    
        contag = (1 + contag / (2 * np.log(m))) * 100  # 转换为百分比
    
        return contag

    def _calculate_metrics(self, raster_path, fishnet_gdf):
        """
        计算景观指标，包括 SHDI、LPI 和 CONTAG
        :param raster_path: 栅格文件路径
        :param fishnet_gdf: 面渔网 GeoDataFrame
        :return: 更新后的面渔网 GeoDataFrame
        """
        # 加载栅格数据
        data, meta = self._load_raster(raster_path)
    
        # 检查栅格坐标系是否为 EPSG:32649
        raster_crs = meta["crs"]
        if raster_crs.to_string() != "EPSG:32649":
            raise ValueError(f"栅格文件的坐标系不是 EPSG:32649，而是 {raster_crs.to_string()}")
    
        # 重投影渔网到栅格的坐标系
        fishnet_gdf = self._reproject_fishnet(fishnet_gdf, raster_crs)
    
        # 创建结果列
        fishnet_gdf["SHDI"] = None
        fishnet_gdf["LPI"] = None
        fishnet_gdf["CONTAG"] = None
    
        # 遍历每个格网，添加进度条
        for idx, row in tqdm(fishnet_gdf.iterrows(), total=len(fishnet_gdf), desc="计算景观指标"):
            # 提取格网范围
            minx, miny, maxx, maxy = row.geometry.bounds
    
            # 转换为栅格范围
            col_start, row_start = ~meta["transform"] * (minx, maxy)
            col_end, row_end = ~meta["transform"] * (maxx, miny)
    
            # 检查裁剪范围是否有效
            if col_start < 0 or row_start < 0 or col_end > data.shape[1] or row_end > data.shape[0]:
                fishnet_gdf.at[idx, "SHDI"] = float("nan")
                fishnet_gdf.at[idx, "LPI"] = float("nan")
                fishnet_gdf.at[idx, "CONTAG"] = float("nan")
                continue
    
            # 裁剪栅格数据
            col_start, col_end = int(col_start), int(col_end)
            row_start, row_end = int(row_start), int(row_end)
            clipped_data = data[row_start:row_end, col_start:col_end]
    
            # 如果裁剪后的栅格数据为空或面积为零，跳过计算
            if clipped_data.size == 0 or (clipped_data != 255).sum() == 0:
                fishnet_gdf.at[idx, "SHDI"] = float("nan")
                fishnet_gdf.at[idx, "LPI"] = float("nan")
                fishnet_gdf.at[idx, "CONTAG"] = float("nan")
                continue
    
            # 计算网格总面积
            total_area = clipped_data.size
    
            # 计算 SHDI
            shdi_value = self._calculate_shdi(clipped_data)
            fishnet_gdf.at[idx, "SHDI"] = shdi_value
    
            # 计算 LPI
            lpi_value = self._calculate_lpi(clipped_data, total_area)
            fishnet_gdf.at[idx, "LPI"] = lpi_value
    
            # 计算 CONTAG
            contag_value = self._calculate_contag(clipped_data, total_area)
            fishnet_gdf.at[idx, "CONTAG"] = contag_value
    
        return fishnet_gdf

    def _save_results(self, fishnet_gdf, raster_name):
        """
        保存结果为新的矢量文件
        :param fishnet_gdf: 更新后的面渔网 GeoDataFrame
        :param raster_name: 栅格文件名称
        """
        # 保留 4 位小数并避免科学计数法
        fishnet_gdf["SHDI"] = fishnet_gdf["SHDI"].apply(lambda x: round(x, 4))
        fishnet_gdf["LPI"] = fishnet_gdf["LPI"].apply(lambda x: round(x, 4))
        fishnet_gdf["CONTAG"] = fishnet_gdf["CONTAG"].apply(lambda x: round(x, 4))
    
        # 根据栅格文件名动态调整保存文件名
        if "2020" in raster_name:
            suffix = "2020_landcover"
        elif "2015" in raster_name:
            suffix = "2015_landcover"
        elif "2030" in raster_name or "Simulation" in raster_name:
            suffix = "2030_prediction"
        else:
            suffix = "unknown"
    
        output_path = os.path.join(self.output_dir, f"fishnet_metrics_{suffix}.shp")
        fishnet_gdf.to_file(output_path, driver="ESRI Shapefile")

    def calculate(self):
        """
        执行景观指标计算任务
        """
        # 加载面渔网
        fishnet_gdf = self._load_fishnet()

        # 遍历栅格文件
        for raster_path in tqdm(self.raster_paths, desc="处理栅格文件"):
            print(f"处理栅格文件: {raster_path}")
            raster_name = os.path.splitext(os.path.basename(raster_path))[0]

            # 计算景观指标
            updated_fishnet_gdf = self._calculate_metrics(raster_path, fishnet_gdf)

            # 保存结果
            self._save_results(updated_fishnet_gdf, raster_name)


if __name__ == "__main__":
    fishnet_path = r"F:\landuse\data\unsignedchar\homework\fishnet\最终26格网非点.shp"
    raster_paths = [
        r"F:\landuse\data\unsignedchar\CLCD_2020.tif",
        r"F:\landuse\data\unsignedchar\CLCD_2015.tif",
        r"F:\landuse\data\unsignedchar\homework\New folder\result1530firstSimulation_1.tif"
    ]
    output_dir = r"F:\landuse\data\unsignedchar\homework\shdi"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    calculator = LandscapeMetricsCalculator(fishnet_path, raster_paths, output_dir)
    calculator.calculate()