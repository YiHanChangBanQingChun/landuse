import os
import rasterio
import numpy as np
from typing import List

class RasterConverter:
    """
    一个用于转换栅格文件数据类型的类。
    """

    def __init__(self, input_dir: str, output_dir: str):
        """
        初始化 RasterConverter 类。

        :param input_dir: str - 输入目录路径，包含以 CLCD 开头且以 _rc.tif 结尾的文件。
        :param output_dir: str - 输出目录路径，转换后的文件将保存到此目录。
        """
        self.input_dir = input_dir
        self.output_dir = output_dir

    def convert_to_unsigned_char(self) -> None:
        """
        将以 CLCD 开头且以 _rc.tif 结尾的文件从 32 位有符号浮点型转换为 unsigned char 类型。
        """
        # 获取目录中符合条件的文件
        tif_files: List[str] = [
            os.path.join(self.input_dir, f) for f in os.listdir(self.input_dir)
            # if f.startswith("CLCD") and f.endswith("_rc.tif")
            if f.startswith("water") and f.endswith("_foshanint3.tif")
        ]

        if not tif_files:
            print(f"目录 {self.input_dir} 中没有找到符合条件的文件。")
            return

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 遍历每个文件进行转换
        for tif_file in tif_files:
            print(f"正在处理文件: {tif_file}")
            with rasterio.open(tif_file) as src:
                # 读取栅格数据
                data = src.read(1)  # 读取第一波段
                nodata_value = src.nodata
                print(f"原始 nodata 值: {nodata_value}")

                # 检查数据是否符合预期值范围
                unique_values = np.unique(data)
                # expected_values = {1, 2, 3, 4, 5, 6, nodata_value}
                expected_values = {0, 1, nodata_value}
                if not set(unique_values).issubset(expected_values):
                    print(f"文件 {tif_file} 包含非预期值，跳过处理。")
                    continue

                # 转换数据类型为 unsigned char
                converted_data = np.copy(data).astype(np.uint8)

                # 更新 nodata 值为 255（适用于 unsigned char 类型）
                converted_data[data == nodata_value] = 255
                new_nodata_value = 255

                # 更新元数据
                out_meta = src.meta.copy()
                out_meta.update({
                    "dtype": "uint8",  # 设置为 unsigned char 类型
                    "nodata": new_nodata_value
                })

                # 构造输出文件路径（文件名保持不变）
                output_file = os.path.join(self.output_dir, os.path.basename(tif_file))

                # 保存转换后的栅格数据
                with rasterio.open(output_file, "w", **out_meta) as dest:
                    dest.write(converted_data, 1)

            print(f"转换完成，保存到: {output_file}")


# 示例调用
if __name__ == "__main__":
    input_directory = "F:/landuse/data/intersection"
    output_directory = "F:/landuse/data/unsignedchar"
    converter = RasterConverter(input_directory, output_directory)
    converter.convert_to_unsigned_char()