import os
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
import geopandas as gpd
import numpy as np
from tqdm import tqdm
from shapely.geometry import box
import pandas as pd

class DEMProcessor:
    def __init__(self, dem_folder, shapefile_path, output_folder):
        """
        初始化 DEMProcessor 对象
        :param dem_folder: DEM 文件所在文件夹路径
        :param shapefile_path: 用于裁剪的矢量文件路径
        :param output_folder: 输出文件夹路径
        """
        self.dem_folder = dem_folder
        self.shapefile_path = shapefile_path
        self.output_folder = output_folder

        # 创建输出文件夹（如果不存在）
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def merge_rasters(self):
        """
        合并栅格 DEM 数据
        :return: 合并后的栅格数据和其元数据
        """
        dem_files = [os.path.join(self.dem_folder, f) for f in os.listdir(self.dem_folder) if f.endswith('.img')]
        rasters = [rasterio.open(dem) for dem in dem_files]

        # 合并栅格数据
        merged_raster, merged_transform = merge(rasters)

        # 获取元数据并更新
        merged_meta = rasters[0].meta.copy()
        merged_meta.update({
            "driver": "GTiff",
            "height": merged_raster.shape[1],
            "width": merged_raster.shape[2],
            "transform": merged_transform,
            "nodata": -9999  # 设置 nodata 值
        })

        return merged_raster, merged_meta

    def check_overlap(raster_bounds, shapefile_bounds):
        """
        检查栅格数据和矢量文件的范围是否重叠
        :param raster_bounds: 栅格数据的范围
        :param shapefile_bounds: 矢量文件的范围
        :return: 是否重叠
        """
        return not (
            raster_bounds[2] < shapefile_bounds[0] or  # 栅格右边界 < 矢量左边界
            raster_bounds[0] > shapefile_bounds[2] or  # 栅格左边界 > 矢量右边界
            raster_bounds[3] < shapefile_bounds[1] or  # 栅格上边界 < 矢量下边界
            raster_bounds[1] > shapefile_bounds[3]     # 栅格下边界 > 矢量上边界
        )

    def clip_raster(self, raster, meta):
        """
        根据矢量文件裁剪栅格数据
        :param raster: 栅格数据
        :param meta: 栅格元数据
        :return: 裁剪后的栅格数据和其元数据
        """
        # 将合并后的栅格数据写入临时文件
        temp_raster_path = os.path.join(self.output_folder, "temp_merged_dem.tif")
        with rasterio.open(temp_raster_path, "w", **meta) as temp_raster:
            temp_raster.write(raster)

        # 读取矢量文件
        shapefile = gpd.read_file(self.shapefile_path)

        # 将矢量文件重新投影到栅格数据的坐标系
        shapefile = DEMProcessor.reproject_shapefile(shapefile, meta["crs"])
        shapes = [feature["geometry"] for feature in shapefile.iterfeatures()]

        # 使用 rasterio 打开临时文件
        with rasterio.open(temp_raster_path) as dataset:
            # 检查范围重叠
            if not DEMProcessor.check_overlap(dataset.bounds, shapefile.total_bounds):
                raise ValueError("矢量文件的范围与栅格数据的范围不重叠。")

            # 裁剪栅格数据
            clipped_raster, clipped_transform = mask(dataset, shapes, crop=True, nodata=meta["nodata"])

        # 更新元数据
        clipped_meta = meta.copy()
        clipped_meta.update({
            "height": clipped_raster.shape[1],
            "width": clipped_raster.shape[2],
            "transform": clipped_transform
        })

        # 删除临时文件
        if os.path.exists(temp_raster_path):
            os.remove(temp_raster_path)

        return clipped_raster, clipped_meta

    def reproject_shapefile(shapefile, raster_crs):
        """
        将矢量文件重新投影到栅格数据的坐标系
        :param shapefile: GeoDataFrame 对象
        :param raster_crs: 栅格数据的坐标系
        :return: 重新投影后的 GeoDataFrame
        """
        if shapefile.crs != raster_crs:
            shapefile = shapefile.to_crs(raster_crs)
        return shapefile

    def save_raster(self, raster, meta, output_path):
        """
        保存栅格数据到文件
        :param raster: 栅格数据
        :param meta: 栅格元数据
        :param output_path: 输出文件路径
        """
        with rasterio.open(output_path, "w", **meta) as dest:
            dest.write(raster)

    def process(self, filesuffix):
        """
        执行合并和裁剪操作
        """
        # 合并栅格数据
        merged_raster, merged_meta = self.merge_rasters()

        # 保存合并后的栅格数据
        merged_output_path = os.path.join(self.output_folder, "merged_dem.tif")
        self.save_raster(merged_raster, merged_meta, merged_output_path)
        print(f"合并后的栅格数据已保存到: {merged_output_path}")

        # 裁剪栅格数据
        clipped_raster, clipped_meta = self.clip_raster(merged_raster, merged_meta)
        clipped_output_path = os.path.join(self.output_folder, f"dem{filesuffix}.tif")
        self.save_raster(clipped_raster, clipped_meta, clipped_output_path)
        print(f"裁剪后的栅格数据已保存到: {clipped_output_path}")

class ShapefileProcessor:
    def __init__(self, input_folder, foshan_shapefile, output_folder, chunk_size=1000):
        """
        初始化 ShapefileProcessor 对象
        :param input_folder: 包含多个 shapefile 的文件夹路径
        :param foshan_shapefile: foshan.shp 文件路径
        :param output_folder: 输出文件夹路径
        :param chunk_size: 每次处理的要素块大小
        """
        self.input_folder = input_folder
        self.foshan_shapefile = foshan_shapefile
        self.output_folder = output_folder
        self.chunk_size = chunk_size

        # 创建输出文件夹（如果不存在）
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def clip_shapefile_chunked(self, input_shapefile, foshan_gdf):
        """
        根据 foshan.shp 对单个 shapefile 进行分块裁剪
        :param input_shapefile: 输入 shapefile 文件路径
        :param foshan_gdf: foshan.shp 的 GeoDataFrame 对象
        :return: 裁剪后的 GeoDataFrame
        """
        # 读取输入 Shapefile 的几何和必要字段
        input_gdf = gpd.read_file(input_shapefile)

        # 确保坐标系一致
        if input_gdf.crs != foshan_gdf.crs:
            input_gdf = input_gdf.to_crs(foshan_gdf.crs)

        # 使用空间索引快速筛选与 foshan.shp 范围相交的要素
        foshan_bounds = box(*foshan_gdf.total_bounds)
        spatial_index = input_gdf.sindex
        possible_matches_index = list(spatial_index.intersection(foshan_bounds.bounds))
        input_gdf = input_gdf.iloc[possible_matches_index]

        # 分块处理
        total_features = len(input_gdf)
        clipped_gdf_list = []
        with tqdm(total=total_features, desc="裁剪要素进度", unit="要素") as feature_pbar:
            for start in range(0, total_features, self.chunk_size):
                end = min(start + self.chunk_size, total_features)
                chunk = input_gdf.iloc[start:end]
                intersection = gpd.overlay(chunk, foshan_gdf, how='intersection')
                clipped_gdf_list.append(intersection)
                feature_pbar.update(len(chunk))

        # 合并所有裁剪结果
        clipped_gdf = gpd.GeoDataFrame(pd.concat(clipped_gdf_list, ignore_index=True), crs=input_gdf.crs)

        return clipped_gdf

    def process(self, filesuffix):
        """
        遍历输入文件夹中的所有 shapefile 文件，执行裁剪并保存结果
        """
        # 读取 foshan.shp
        foshan_gdf = gpd.read_file(self.foshan_shapefile)

        # 获取所有 shapefile 文件
        shapefiles = [f for f in os.listdir(self.input_folder) if f.endswith('.shp')]

        # 使用 tqdm 显示总进度
        with tqdm(total=len(shapefiles), desc="总进度", unit="文件") as pbar:
            for filename in shapefiles:
                input_shapefile = os.path.join(self.input_folder, filename)

                # 检查是否已处理过该文件
                output_shapefile = os.path.join(self.output_folder, f"{os.path.splitext(filename)[0]}_{filesuffix}.shp")
                if os.path.exists(output_shapefile):
                    print(f"文件已处理，跳过: {filename}")
                    pbar.update(1)
                    continue

                # 显示单个文件的处理进度
                print(f"开始处理文件: {filename}")
                clipped_gdf = self.clip_shapefile_chunked(input_shapefile, foshan_gdf)

                # 保存裁剪结果为 Shapefile 格式
                clipped_gdf.to_file(output_shapefile, driver="ESRI Shapefile",encoding="utf-8")
                print(f"裁剪后的文件已保存到: {output_shapefile}")

                pbar.update(1)  # 更新总进度


def test_shapefileclip_main():
    """
    测试函数，执行 ShapefileProcessor 的主要功能
    """
    input_folder = r"F:\landuse\data\poiraw"
    foshan_shapefile = r"F:\landuse\data\foshan\foshan.shp"
    output_folder = r"F:\landuse\data\foshanroadpoi"
    filesuffix = "foshan"
    processor = ShapefileProcessor(input_folder, foshan_shapefile, output_folder, chunk_size=1000)
    processor.process(filesuffix)

def test_demclip_main():
    """
    测试函数，执行 DEMProcessor 的主要功能
    """
    dem_folder = r"F:\landuse\data\dem"
    shapefile_path = r"F:\landuse\data\foshan\foshan.shp"
    output_folder = r"F:\landuse\data\dem\mergedem"
    filesuffix = "foshan"
    processor = DEMProcessor(dem_folder, shapefile_path, output_folder)
    processor.process(filesuffix)

if __name__ == "__main__":
    # test_demclip_main()
    test_shapefileclip_main()