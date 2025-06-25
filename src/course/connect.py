import os
import geopandas as gpd

class ShapefileMerger:
    def __init__(self, folder1, folder2, output_folder):
        """
        初始化 Shapefile 合并器
        :param folder1: 第一个文件夹路径，包含 SHDI 的 Shapefile
        :param folder2: 第二个文件夹路径，包含其他指标的 Shapefile
        :param output_folder: 输出文件夹路径，用于保存合并后的 Shapefile
        """
        self.folder1 = folder1
        self.folder2 = folder2
        self.output_folder = output_folder

    def _get_shapefile_paths(self, folder):
        """
        获取文件夹中所有 .shp 文件的路径
        :param folder: 文件夹路径
        :return: .shp 文件路径列表
        """
        return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".shp")]

    def _find_matching_files(self, files1, files2):
        """
        找到两个文件夹中所有相同名字的 .shp 文件
        :param files1: 第一个文件夹中的 .shp 文件路径列表
        :param files2: 第二个文件夹中的 .shp 文件路径列表
        :return: 匹配的文件名列表
        """
        names1 = {os.path.splitext(os.path.basename(f))[0] for f in files1}
        names2 = {os.path.splitext(os.path.basename(f))[0] for f in files2}
        return names1.intersection(names2)

    def _merge_shapefiles(self, file1, file2, output_path):
        """
        合并两个 Shapefile 的属性表，根据相同 geometry 进行匹配
        :param file1: 第一个 Shapefile 文件路径
        :param file2: 第二个 Shapefile 文件路径
        :param output_path: 输出文件路径
        """
        # 加载两个 Shapefile
        gdf1 = gpd.read_file(file1)
        gdf2 = gpd.read_file(file2)
        print(f"加载文件: {file1} 和 {file2}")
        # 打印列名
        print(f"文件 {file1} 列名: {gdf1.columns.tolist()}")
        print(f"文件 {file2} 列名: {gdf2.columns.tolist()}")
    
        # 确保两个 Shapefile 都有 geometry 列
        if "geometry" not in gdf1.columns or "geometry" not in gdf2.columns:
            raise ValueError(f"文件 {file1} 或 {file2} 缺少 geometry 列")
    
        # 根据 geometry 进行匹配
        merged_gdf = gpd.sjoin(gdf1, gdf2, how="inner", predicate="intersects")
    
        # 保存合并后的 Shapefile
        merged_gdf.to_file(output_path, driver="ESRI Shapefile")

    def merge_all(self):
        """
        执行 Shapefile 合并任务
        """
        # 获取两个文件夹中的所有 .shp 文件路径
        files1 = self._get_shapefile_paths(self.folder1)
        files2 = self._get_shapefile_paths(self.folder2)

        # 找到两个文件夹中所有相同名字的 .shp 文件
        matching_files = self._find_matching_files(files1, files2)

        # 确保输出文件夹存在
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # 合并每对匹配的 Shapefile
        for name in matching_files:
            file1 = os.path.join(self.folder1, f"{name}.shp")
            file2 = os.path.join(self.folder2, f"{name}.shp")
            output_path = os.path.join(self.output_folder, f"{name}_merged.shp")

            print(f"合并文件: {file1} 和 {file2} 到 {output_path}")
            self._merge_shapefiles(file1, file2, output_path)


if __name__ == "__main__":
    # 文件夹路径
    folder1 = r"F:\landuse\data\unsignedchar\homework\shdi"
    folder2 = r"F:\landuse\data\unsignedchar\homework\metrics"
    output_folder = r"F:\landuse\data\unsignedchar\homework\merged"

    # 初始化合并器并执行任务
    merger = ShapefileMerger(folder1, folder2, output_folder)
    merger.merge_all()