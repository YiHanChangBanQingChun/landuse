import os
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from osgeo import gdal
from pyproj import CRS
from tqdm import tqdm
import numpy as np
import fiona

class RasterProcessor:
    def __init__(self, raster_paths, shp_path, reference_raster_path, output_dir):
        """
        初始化栅格处理器
        :param raster_paths: 输入栅格影像路径列表
        :param shp_path: 面状矢量文件路径（用于参考坐标系和掩膜）
        :param reference_raster_path: 参考栅格影像路径（用于对齐和分辨率）
        :param output_dir: 输出栅格影像目录
        """
        self.raster_paths = raster_paths
        self.shp_path = shp_path
        self.reference_raster_path = reference_raster_path
        self.output_dir = output_dir

    def get_crs_from_shp(self):
        """
        从矢量文件中获取投影坐标系
        :return: 投影坐标系的 EPSG 编号
        """
        with fiona.open(self.shp_path, "r") as shapefile:
            shp_crs = shapefile.crs
            if "init" in shp_crs:
                epsg_code = shp_crs["init"].split(":")[1]
                return int(epsg_code)
            else:
                raise ValueError("无法从矢量文件中提取 EPSG 坐标系")

    def apply_mask(self, raster_path, output_path):
        """
        使用矢量文件对栅格数据进行掩膜操作，将矢量范围外的区域设置为 NoData (-9999)
        :param raster_path: 输入栅格路径
        :param output_path: 输出栅格路径
        """
        with fiona.open(self.shp_path, "r") as shapefile:
            shapes = [feature["geometry"] for feature in shapefile]
    
        with rasterio.open(raster_path) as src:
            # 掩膜操作，设置 nodata 为 -9999
            out_image, out_transform = mask(src, shapes, crop=True, nodata=-9999)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": -9999  # 设置输出栅格的 NoData 值
            })
    
            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(out_image)
        print(f"掩膜完成，保存到: {output_path}")

    def reproject_raster(self, raster_path, output_path):
        """
        将栅格影像重投影到矢量文件的坐标系，并调整分辨率为 30 米
        :param raster_path: 输入栅格路径
        :param output_path: 输出栅格路径
        """
        with rasterio.open(raster_path) as src:
            # 获取栅格的当前坐标系
            src_crs = src.crs
            print(f"输入栅格的坐标系: {src_crs}")

            # 获取目标坐标系
            target_crs = CRS.from_epsg(self.get_crs_from_shp())
            print(f"目标坐标系: {target_crs}")

            # 计算重投影参数
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds, resolution=(30, 30)
            )

            # 创建重投影后的栅格
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height
            })

            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear
                    )
        print(f"重投影完成，保存到: {output_path}")

    def align_to_reference(self, masked_path, aligned_path):
        """
        将栅格影像与参考栅格对齐，并确保 NoData 值正确设置
        :param masked_path: 掩膜后的栅格路径
        :param aligned_path: 对齐后的栅格路径
        """
        reference_ds = gdal.Open(self.reference_raster_path)
        target_ds = gdal.Open(masked_path)
    
        # 获取参考栅格的地理信息
        reference_geo_transform = reference_ds.GetGeoTransform()
        reference_projection = reference_ds.GetProjection()
    
        # 创建对齐后的栅格
        driver = gdal.GetDriverByName('GTiff')
        aligned_ds = driver.Create(
            aligned_path,
            reference_ds.RasterXSize,
            reference_ds.RasterYSize,
            target_ds.RasterCount,
            gdal.GDT_Float32
        )
    
        aligned_ds.SetGeoTransform(reference_geo_transform)
        aligned_ds.SetProjection(reference_projection)
    
        # 设置 NoData 值
        nodata_value = -9999
        for band_index in range(1, target_ds.RasterCount + 1):
            aligned_ds.GetRasterBand(band_index).SetNoDataValue(nodata_value)
    
        # 对齐并插值
        gdal.ReprojectImage(
            target_ds,
            aligned_ds,
            target_ds.GetProjection(),
            reference_projection,
            gdal.GRA_Bilinear
        )
    
        aligned_ds.FlushCache()
        print(f"对齐完成，保存到: {aligned_path}")

    def normalize_raster(self, input_path, output_path):
        """
        对栅格影像进行归一化处理，仅对有效数据区域进行归一化
        :param input_path: 输入栅格路径
        :param output_path: 输出归一化栅格路径
        """
        with rasterio.open(input_path) as src:
            data = src.read(1)  # 读取第一波段数据
            nodata_value = src.nodata
    
            # 仅对有效数据区域进行归一化
            valid_mask = data != nodata_value
            if np.any(valid_mask):
                min_val = np.min(data[valid_mask])
                max_val = np.max(data[valid_mask])
                normalized_data = np.zeros_like(data, dtype=np.float32)
                normalized_data[valid_mask] = (data[valid_mask] - min_val) / (max_val - min_val)
    
                # 更新元数据
                out_meta = src.meta.copy()
                out_meta.update({
                    "dtype": "float32",
                    "nodata": nodata_value
                })
    
                # 保存归一化后的栅格
                with rasterio.open(output_path, "w", **out_meta) as dst:
                    dst.write(normalized_data, 1)
            print(f"归一化完成，保存到: {output_path}")

    def calculate_and_apply_intersection(self, aligned_tifs, reference_tifs, output_dir):
        """
        计算所有栅格的有数据区域交集，并对每个栅格文件进行裁剪，确保有数据区域完全对齐。
        :param aligned_tifs: 对齐后的栅格文件列表（a开头的文件）
        :param reference_tifs: 参考栅格文件列表（2005, 2010, 2015, 2020的文件）
        :param output_dir: 输出裁剪后的栅格文件目录
        """
        all_tifs = aligned_tifs + reference_tifs
        masks = []
    
        # 读取所有栅格的有效数据区域
        for tif in all_tifs:
            with rasterio.open(tif) as src:
                data = src.read(1)
                nodata_value = src.nodata
                mask = data != nodata_value  # 有效数据区域
                masks.append(mask)
    
        # 计算所有栅格的交集
        intersection_mask = np.logical_and.reduce(masks)
    
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
        # 对每个栅格文件进行裁剪
        for tif in all_tifs:
            with rasterio.open(tif) as src:
                data = src.read(1)
                out_meta = src.meta.copy()
                out_meta.update({
                    "dtype": "float32",
                    "nodata": -9999
                })
    
                # 创建裁剪后的栅格数据
                clipped_data = np.zeros_like(data, dtype=np.float32)
                clipped_data[intersection_mask] = data[intersection_mask]
    
                # 保存裁剪后的栅格到指定目录，文件名保持不变
                output_path = os.path.join(output_dir, os.path.basename(tif))
                with rasterio.open(output_path, "w", **out_meta) as dst:
                    dst.write(clipped_data, 1)
    
            print(f"裁剪完成，保存到: {output_path}")

    def process(self,normalize=True):
        """
        执行栅格处理流程
        """
        for raster_path in tqdm(self.raster_paths, desc="处理栅格影像"):
            if normalize is True:
                print(f"处理栅格影像: {raster_path}")
                raster_name = os.path.basename(raster_path)
                reprojected_path = os.path.join(self.output_dir, f"r_{raster_name}")
                normalized_path = os.path.join(self.output_dir, f"n_{raster_name}")
                masked_path = os.path.join(self.output_dir, f"m_{raster_name}")
                aligned_path = os.path.join(self.output_dir, f"a_{raster_name}")

                # 重投影
                self.reproject_raster(raster_path, reprojected_path)

                # 归一化
                self.normalize_raster(reprojected_path, normalized_path)

                # 掩膜
                self.apply_mask(normalized_path, masked_path)

                # 对齐
                self.align_to_reference(masked_path, aligned_path)
            else:
                print(f"处理栅格影像: {raster_path}")
                raster_name = os.path.basename(raster_path)
                reprojected_path = os.path.join(self.output_dir, f"r_{raster_name}")
                masked_path = os.path.join(self.output_dir, f"m_{raster_name}")
                aligned_path = os.path.join(self.output_dir, f"a_{raster_name}")
                # 重投影
                self.reproject_raster(raster_path, reprojected_path)
                # 掩膜
                self.apply_mask(reprojected_path, masked_path)
                # 对齐
                self.align_to_reference(masked_path, aligned_path)

    def apply_mask_to_intersection(self, intersection_dir):
        """
        对交集裁剪后的栅格文件进行掩膜处理，将矢量范围外的区域设置为 NoData (-9999)。
        :param intersection_dir: 交集裁剪后的栅格文件目录
        """
        # 获取交集裁剪后的栅格文件列表
        intersection_tifs = [os.path.join(intersection_dir, f) for f in os.listdir(intersection_dir) if f.endswith(".tif")]
    
        for tif in intersection_tifs:
            with fiona.open(self.shp_path, "r") as shapefile:
                shapes = [feature["geometry"] for feature in shapefile]
    
            with rasterio.open(tif) as src:
                # 掩膜操作，设置 nodata 为 -9999
                out_image, out_transform = mask(src, shapes, crop=True, nodata=-9999)
                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "nodata": -9999  # 设置输出栅格的 NoData 值
                })
    
                # 使用临时文件保存掩膜结果
                temp_output_path = tif + ".tmp"
                with rasterio.open(temp_output_path, "w", **out_meta) as dest:
                    dest.write(out_image)
    
            # 替换原文件
            os.remove(tif)  # 删除原文件
            os.rename(temp_output_path, tif)  # 重命名临时文件为原文件名
            print(f"掩膜完成，保存到: {tif}")

    def apply_clcd_mask_and_update_intersection(self, clcd_paths, intersection_dir):
        """
        对多个 CLCD 栅格文件中值为 0 的区域进行掩膜处理，将这些区域设置为 NoData (2.1474836e+09)，
        并更新交集裁剪后的栅格文件，使这些区域在其他栅格文件中也被设置为 NoData (-9999)。
        CLCD 数据在处理前转换为 32 位有符号整型，最后保存为 32 位有符号整型，nodata 值设置为 2.1474836e+09。
        :param clcd_paths: CLCD 栅格文件路径列表
        :param intersection_dir: 交集裁剪后的栅格文件目录
        """
        # 初始化总掩膜
        combined_mask = None
    
        # 遍历所有 CLCD 文件，生成总掩膜
        for clcd_path in clcd_paths:
            with rasterio.open(clcd_path) as clcd_src:
                clcd_data = clcd_src.read(1).astype(np.int32)  # 转换为 32 位有符号整型
                clcd_nodata_value = np.int32(2.1474836e+09)  # 设置 nodata 值为 2.1474836e+09
    
                # 创建掩膜：值为 0 的区域
                clcd_mask = clcd_data == 0
    
                # 打印当前 CLCD 文件中值为 0 的区域行列号
                zero_indices = np.argwhere(clcd_mask)
                print(f"{os.path.basename(clcd_path)} 值为 0 的区域行列号: {zero_indices}")
    
                # 将值为 0 的区域设置为 nodata 值
                clcd_data[clcd_mask] = clcd_nodata_value
    
                # 保存更新后的 CLCD 数据为 32 位有符号整型
                clcd_output_path = os.path.join(intersection_dir, os.path.basename(clcd_path))
                clcd_meta = clcd_src.meta.copy()
                clcd_meta.update({
                    "nodata": clcd_nodata_value,
                    "dtype": "int32"  # 设置为 32 位有符号整型
                })
                with rasterio.open(clcd_output_path, "w", **clcd_meta) as clcd_dest:
                    clcd_dest.write(clcd_data, 1)
                print(f"{os.path.basename(clcd_path)} 数据处理完成，保存到: {clcd_output_path}")
    
                # 合并掩膜
                if combined_mask is None:
                    combined_mask = clcd_mask
                else:
                    combined_mask = np.logical_or(combined_mask, clcd_mask)
    
        # 获取交集裁剪后的栅格文件列表
        intersection_tifs = [os.path.join(intersection_dir, f) for f in os.listdir(intersection_dir) if f.endswith(".tif")]
    
        # 对每个栅格文件应用更新的掩膜逻辑
        for tif in intersection_tifs:
            with rasterio.open(tif) as src:
                data = src.read(1)
                nodata_value = src.nodata
    
                # 更新掩膜：将所有 CLCD 中值为 0 的区域设置为 NoData (-9999)
                updated_data = np.copy(data)
                updated_data[combined_mask] = -9999
    
                # 更新元数据
                out_meta = src.meta.copy()
                out_meta.update({
                    "nodata": -9999,
                    "dtype": "float32"  # 确保输出为 32 位浮点型
                })
    
                # 保存更新后的栅格文件
                temp_output_path = tif + ".tmp"
                with rasterio.open(temp_output_path, "w", **out_meta) as dest:
                    dest.write(updated_data, 1)
    
            # 替换原文件
            os.remove(tif)  # 删除原文件
            os.rename(temp_output_path, tif)  # 重命名临时文件为原文件名
            print(f"更新掩膜完成，保存到: {tif}")

def test_raster_processor():
    """
    测试 RasterProcessor 类
    """
    # 输入参数
    raster_paths = [
        "F:/landuse/data/dem/mergedem/demfoshan.tif",
        "F:/landuse/data/dem/mergedem/foshanslope.tif",
        "F:/landuse/data/population/foshanpopulation.tif",
        "F:/landuse/data/temp/foshantemp.tif",
        "F:/landuse/data/distance/dis_primary.tif",
        "F:/landuse/data/distance/dis_secondary.tif",
        "F:/landuse/data/distance/dis_tertiary.tif",
        "F:/landuse/data/distance/dis_foshannatural.tif",
        "F:/landuse/data/distance/dis_foshanregion.tif",
        "F:/landuse/data/distance/dis_railways.tif",
        "F:/landuse/data/density/density_poi.tif",
        "F:/landuse/data/water/fswater.tif",
    ]
    shp_path = "F:/landuse/data/foshan/foshan.shp"
    reference_raster_path = "F:/landuse/data/landuse/CLCD_2005_foshan.tif"
    reference_tifs = [
        "F:/landuse/data/landuse/CLCD_2005_foshan.tif",
        "F:/landuse/data/landuse/CLCD_2010_foshan.tif",
        "F:/landuse/data/landuse/CLCD_2015_foshan.tif",
        "F:/landuse/data/landuse/CLCD_2020_foshan.tif"
    ]
    output_dir = "F:/landuse/data/aligndata2"
    intersection_output_dir = "F:/landuse/data/intersection2"

    # 创建文件夹
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(intersection_output_dir):
        os.makedirs(intersection_output_dir)
    # 创建处理器并执行处理
    processor = RasterProcessor(raster_paths, shp_path, reference_raster_path, output_dir)
    processor.process(normalize=False)

    # 获取所有对齐后的栅格文件（a开头的文件）
    aligned_tifs = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("a_")]

    # 计算交集并裁剪每个栅格文件，保存到指定目录
    processor.calculate_and_apply_intersection(aligned_tifs, reference_tifs, intersection_output_dir)

    # 对交集裁剪后的栅格文件进行掩膜处理
    processor.apply_mask_to_intersection(intersection_output_dir)

    # 对指定 CLCD 栅格文件中值为 0 的区域进行掩膜处理，并更新交集掩膜逻辑
    # CLCD 文件路径列表
    clcd_paths = [
        "F:/landuse/data/landuse/CLCD_2005_foshan.tif",
        "F:/landuse/data/landuse/CLCD_2010_foshan.tif",
        "F:/landuse/data/landuse/CLCD_2015_foshan.tif",
        "F:/landuse/data/landuse/CLCD_2020_foshan.tif"
    ]
    processor.apply_clcd_mask_and_update_intersection(clcd_paths, intersection_output_dir)

if __name__ == "__main__":
    test_raster_processor()