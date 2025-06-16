import os
import rasterio
import numpy as np
from typing import List

def reclassify_CLCD_tifs(input_dir: str, output_suffix: str = "rc") -> None:
    """
    读取指定目录下以 'CLCD' 开头的所有 .tif 文件，将栅格值 7 改为 3，8 改为 6，
    并将结果保存到同一位置，文件名后缀增加指定后缀。

    :param input_dir: str - 输入目录路径，包含以 'CLCD' 开头的 .tif 文件
    :param output_suffix: str - 输出文件名后缀，默认为 'rc'
    """
    # 获取目录中以 'CLCD' 开头的所有 .tif 文件
    tif_files: List[str] = [
        os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.startswith("CLCD") and f.endswith(".tif")
    ]

    if not tif_files:
        print(f"目录 {input_dir} 中没有找到以 'CLCD' 开头的 .tif 文件。")
        return

    # 遍历每个文件进行重分类
    for tif_file in tif_files:
        print(f"正在处理文件: {tif_file}")
        with rasterio.open(tif_file) as src:
            # 读取栅格数据
            data = src.read(1)  # 读取第一波段
            nodata_value = src.nodata

            # 创建重分类后的数据
            reclassified_data = np.copy(data)
            reclassified_data[data == 7] = 3  # 将值 7 改为 3
            reclassified_data[data == 8] = 6  # 将值 8 改为 6

            # 更新元数据
            out_meta = src.meta.copy()

            # 构造输出文件路径
            output_file = os.path.join(
                input_dir, f"{os.path.splitext(os.path.basename(tif_file))[0]}_{output_suffix}.tif"
            )

            # 保存重分类后的栅格数据
            with rasterio.open(output_file, "w", **out_meta) as dest:
                dest.write(reclassified_data, 1)

        print(f"重分类完成，保存到: {output_file}")

# 示例调用
if __name__ == "__main__":
    input_directory = "F:/landuse/data/intersection"
    reclassify_CLCD_tifs(input_directory)