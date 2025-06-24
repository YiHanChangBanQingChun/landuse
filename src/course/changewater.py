import rasterio
from rasterio.features import geometry_mask
import geopandas as gpd
import numpy as np
import os

class RasterModifier:
    def __init__(self, raster_path, nowater_shapefile, protection_shapefile, output_path):
        """
        初始化栅格修改类
        :param raster_path: 输入栅格文件路径
        :param nowater_shapefile: 修改为1的矢量文件路径
        :param protection_shapefile: 修改为0的矢量文件路径
        :param output_path: 输出栅格文件路径
        """
        self.raster_path = raster_path
        self.nowater_shapefile = nowater_shapefile
        self.protection_shapefile = protection_shapefile
        self.output_path = output_path

    def modify_raster(self):
        """
        修改栅格值并保存为新的文件
        """
        # 读取栅格数据
        with rasterio.open(self.raster_path) as src:
            data = src.read(1)  # 读取第一波段数据
            transform = src.transform
            nodata = src.nodata
            profile = src.profile

            # 创建一个临时浮点数组来处理数据
            temp_data = data.astype(float)
            temp_data[temp_data == nodata] = np.nan  # 将 nodata 值标记为 NaN

            # 读取矢量数据
            nowater_shapes = gpd.read_file(self.nowater_shapefile).geometry
            protection_shapes = gpd.read_file(self.protection_shapefile).geometry

            # 创建掩膜并修改栅格值
            nowater_mask = geometry_mask(nowater_shapes, transform=transform, invert=True, out_shape=temp_data.shape)
            protection_mask = geometry_mask(protection_shapes, transform=transform, invert=True, out_shape=temp_data.shape)

            # 修改规则
            temp_data[(nowater_mask) & (temp_data == 0)] = 1  # 如果面内栅格值为0，则修改为1
            temp_data[(protection_mask) & (temp_data == 1)] = 0  # 如果面内栅格值为1，则修改为0

            # 恢复 nodata 值
            temp_data[np.isnan(temp_data)] = nodata

            # 转换回 uint8 类型
            data = temp_data.astype(np.uint8)

        # 保存修改后的栅格数据
        profile.update(dtype=rasterio.uint8, nodata=nodata)
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with rasterio.open(self.output_path, 'w', **profile) as dst:
            dst.write(data, 1)

if __name__ == "__main__":
    raster_path = r"F:\landuse\data\unsignedchar\restrict.tif"
    nowater_shapefile = r"F:\landuse\data\changewater2no\nowater.shp"
    protection_shapefile = r"F:\landuse\data\protect\protection.shp"
    output_path = r"F:\landuse\data\double\newrestrit\mod_restrict.tif"

    modifier = RasterModifier(raster_path, nowater_shapefile, protection_shapefile, output_path)
    modifier.modify_raster()