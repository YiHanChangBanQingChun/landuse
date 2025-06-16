import os
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
import numpy as np
from scipy.spatial import KDTree
from tqdm import tqdm

class RoadDistanceRasterizer:
    def __init__(self, road_shp_path, foshan_shp_path, output_dir, resolution=30):
        """
        初始化路网栅格化处理器
        :param road_shp_path: 路网矢量文件路径
        :param foshan_shp_path: 佛山面矢量文件路径（用于参考范围和坐标系）
        :param output_dir: 输出栅格文件目录
        :param resolution: 栅格分辨率（单位：米）
        """
        self.road_shp_path = road_shp_path
        self.foshan_shp_path = foshan_shp_path
        self.output_dir = output_dir
        self.resolution = resolution

        # 检查并创建输出目录
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"输出目录 {self.output_dir} 已创建。")

    def reproject_shp(self, input_shp_path, target_crs):
        """
        重投影矢量文件到目标坐标系
        :param input_shp_path: 输入矢量文件路径
        :param target_crs: 目标坐标系（EPSG 编号）
        :return: 重投影后的 GeoDataFrame
        """
        gdf = gpd.read_file(input_shp_path)
        gdf = gdf.to_crs(epsg=target_crs)
        return gdf

    def create_raster_from_class(self, road_gdf, foshan_gdf, class_field):
        """
        根据路网的 class 字段创建栅格文件
        :param road_gdf: 路网 GeoDataFrame
        :param foshan_gdf: 佛山面 GeoDataFrame
        :param class_field: 用于分类的字段名
        """
        # 获取佛山面范围和分辨率
        bounds = foshan_gdf.total_bounds
        minx, miny, maxx, maxy = bounds
        width = int((maxx - minx) / self.resolution)
        height = int((maxy - miny) / self.resolution)
        transform = from_origin(minx, maxy, self.resolution, self.resolution)
    
        # 分类处理
        unique_classes = road_gdf[class_field].unique()
        for road_class in tqdm(unique_classes, desc="处理路网分类"):
            # 筛选当前类别的路网
            class_gdf = road_gdf[road_gdf[class_field] == road_class]
    
            # 提取路网的所有坐标点
            points = []
            for _, row in class_gdf.iterrows():
                geometry = row.geometry
                if geometry.geom_type == "MultiLineString":
                    geometries = geometry.geoms
                else:
                    geometries = [geometry]
    
                for geom in geometries:
                    points.extend(geom.coords)
    
            # 如果没有点，跳过处理
            if not points:
                print(f"警告: 类别 {road_class} 的路网没有有效点，跳过处理。")
                continue
    
            # 构建 KDTree
            tree = KDTree(points)
    
            # 创建栅格
            x_coords = np.arange(width)
            y_coords = np.arange(height)
            xx, yy = np.meshgrid(x_coords, y_coords)
            px, py = transform * (xx, yy)
            pixel_coords = np.column_stack([px.ravel(), py.ravel()])
            distances, _ = tree.query(pixel_coords)
            raster = distances.reshape(height, width)
    
            # 归一化距离
            # raster_min = raster.min()
            # raster_max = raster.max()
            # raster = (raster - raster_min) / (raster_max - raster_min)
    
            # 保存栅格文件
            output_path = os.path.join(self.output_dir, f"dis_{road_class}.tif")
            with rasterio.open(
                output_path,
                "w",
                driver="GTiff",
                height=height,
                width=width,
                count=1,
                dtype=raster.dtype,
                crs=foshan_gdf.crs.to_string(),
                transform=transform,
            ) as dst:
                dst.write(raster, 1)
            print(f"栅格文件保存到: {output_path}")

    def process(self, class_field):
        """
        执行路网栅格化处理流程
        :param class_field: 用于分类的字段名
        """
        # 重投影路网和佛山面
        foshan_gdf = self.reproject_shp(self.foshan_shp_path, target_crs=32649)
        road_gdf = self.reproject_shp(self.road_shp_path, target_crs=32649)

        # 创建栅格文件
        self.create_raster_from_class(road_gdf, foshan_gdf, class_field)

class PointDistanceRasterizer:
    def __init__(self, point_shp_path, foshan_shp_path, output_dir, resolution=30):
        """
        初始化点栅格化处理器
        :param point_shp_path: 点矢量文件路径
        :param foshan_shp_path: 佛山面矢量文件路径（用于参考范围和坐标系）
        :param output_dir: 输出栅格文件目录
        :param resolution: 栅格分辨率（单位：米）
        """
        self.point_shp_path = point_shp_path
        self.foshan_shp_path = foshan_shp_path
        self.output_dir = output_dir
        self.resolution = resolution

        # 检查并创建输出目录
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"输出目录 {self.output_dir} 已创建。")

    def reproject_shp(self, input_shp_path, target_crs):
        """
        重投影矢量文件到目标坐标系
        :param input_shp_path: 输入矢量文件路径
        :param target_crs: 目标坐标系（EPSG 编号）
        :return: 重投影后的 GeoDataFrame
        """
        gdf = gpd.read_file(input_shp_path)
        gdf = gdf.to_crs(epsg=target_crs)
        return gdf

    def create_raster_from_points(self, point_gdf, foshan_gdf):
        """
        根据点矢量文件创建栅格文件
        :param point_gdf: 点 GeoDataFrame
        :param foshan_gdf: 佛山面 GeoDataFrame
        """
        # 获取佛山面范围和分辨率
        bounds = foshan_gdf.total_bounds
        minx, miny, maxx, maxy = bounds
        width = int((maxx - minx) / self.resolution)
        height = int((maxy - miny) / self.resolution)
        transform = from_origin(minx, maxy, self.resolution, self.resolution)

        # 提取点的坐标
        points = np.array(list(point_gdf.geometry.apply(lambda geom: (geom.x, geom.y))))

        # 如果没有点，跳过处理
        if points.size == 0:
            print(f"警告: 点文件没有有效点，跳过处理。")
            return

        # 构建 KDTree
        tree = KDTree(points)

        # 创建栅格
        x_coords = np.arange(width)
        y_coords = np.arange(height)
        xx, yy = np.meshgrid(x_coords, y_coords)
        px, py = transform * (xx, yy)
        pixel_coords = np.column_stack([px.ravel(), py.ravel()])
        distances, _ = tree.query(pixel_coords)
        raster = distances.reshape(height, width)

        # 归一化距离
        # raster_min = raster.min()
        # raster_max = raster.max()
        # raster = (raster - raster_min) / (raster_max - raster_min)

        # 获取输入文件名作为输出文件名的一部分
        input_filename = os.path.splitext(os.path.basename(self.point_shp_path))[0]
        output_path = os.path.join(self.output_dir, f"dis_{input_filename}.tif")

        # 保存栅格文件
        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=raster.dtype,
            crs=foshan_gdf.crs.to_string(),
            transform=transform,
        ) as dst:
            dst.write(raster, 1)
        print(f"栅格文件保存到: {output_path}")

    def process(self):
        """
        执行点栅格化处理流程
        """
        # 重投影点文件和佛山面
        foshan_gdf = self.reproject_shp(self.foshan_shp_path, target_crs=32649)
        point_gdf = self.reproject_shp(self.point_shp_path, target_crs=32649)

        # 创建栅格文件
        self.create_raster_from_points(point_gdf, foshan_gdf)

def test_point_distance_rasterizer():
    """
    测试 PointDistanceRasterizer 类
    """
    # 输入参数
    point_shp_path_region = "F:/landuse/data/foshanroadpoi/foshanregion.shp"
    point_shp_path_natural = "F:/landuse/data/foshanroadpoi/foshannatural.shp"
    foshan_shp_path = "F:/landuse/data/foshan/foshan.shp"
    output_dir = "F:/landuse/data/distance"

    # 创建处理器并执行处理
    print("处理 foshanregion.shp...")
    rasterizer_region = PointDistanceRasterizer(point_shp_path_region, foshan_shp_path, output_dir)
    rasterizer_region.process()

    print("处理 foshannatural.shp...")
    rasterizer_natural = PointDistanceRasterizer(point_shp_path_natural, foshan_shp_path, output_dir)
    rasterizer_natural.process()

def test_road_distance_rasterizer():
    """
    测试 RoadDistanceRasterizer 类
    """
    # 输入参数
    # road_shp_path = "F:/landuse/data/foshanroadpoi/foshanroad.shp"
    railway_shp_path = "F:/landuse/data/foshanroadpoi/foshanrailways.shp"
    foshan_shp_path = "F:/landuse/data/foshan/foshan.shp"
    output_dir = "F:/landuse/data/distance"
    class_field = "class"

    # 创建处理器并执行处理
    # rasterizer = RoadDistanceRasterizer(road_shp_path, foshan_shp_path, output_dir)
    rasterizer = RoadDistanceRasterizer(railway_shp_path, foshan_shp_path, output_dir)
    rasterizer.process(class_field)

if __name__ == "__main__":
    test_road_distance_rasterizer()
    # test_point_distance_rasterizer()