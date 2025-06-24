import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

class ContributionVisualizer:
    def __init__(self, csv_dir, output_dir):
        """
        初始化贡献度可视化类
        :param csv_dir: CSV文件夹路径
        :param output_dir: 输出图片保存路径
        """
        self.csv_dir = csv_dir
        self.output_dir = output_dir

        # 定义地类名称
        self.land_types = ["农田", "森林", "荒地", "草原", "水域", "不透水面"]

        # 定义因子名称
        self.factors = [
            "DEM高程", "POI密度", "距离景点距离", "距离区政府中心距离",
            "距离一级道路", "距离高铁地铁", "距离二级道路", "距离三级道路",
            "人口密度", "坡度", "平均温度"
        ]

        # 设置中文字体支持
        rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
        rcParams['axes.unicode_minus'] = False   # 解决负号显示问题

    def _load_data(self):
        """
        加载所有CSV文件数据
        :return: 包含所有地类数据的列表
        """
        data = []
        for i in range(len(self.land_types)):
            file_path = os.path.join(self.csv_dir, f"Contribution{i}.csv")
            # 读取CSV文件并解析数据
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # 提取 RMSE_original
            rmse_original = float(lines[0].split(",")[1].strip())
            
            # 提取因子名称
            factors_line = lines[1].split(",")[1:]  # 从第二行提取因子名称
            factors = [factor.strip() for factor in factors_line if factor.strip()]  # 去除空值和多余空格
            
            # 检查因子名称是否完整
            if len(factors) != len(self.factors):
                raise ValueError(f"因子数量不匹配！预期 {len(self.factors)} 个因子，但在文件中找到 {len(factors)} 个因子。")
    
            # 提取 RMSE_noise，过滤空值
            rmse_noise = [float(value) for value in lines[2].split(",")[1:] if value.strip()]
            
            # 提取 Contribution，过滤空值
            contribution = [float(value) for value in lines[3].split(",")[1:] if value.strip()]
            print(f"地类 {self.land_types[i]} 的 RMSE_original: {rmse_original}, RMSE_noise: {rmse_noise}, Contribution: {contribution}")
            
            data.append({
                "land_type": self.land_types[i],
                "rmse_original": rmse_original,
                "rmse_noise": rmse_noise,
                "contribution": contribution
            })
        return data

    def plot_rmse_original(self, data):
        """
        绘制RMSE_original柱状图
        :param data: 加载的地类数据
        """
        land_types = [d["land_type"] for d in data]
        rmse_values = [d["rmse_original"] for d in data]

        plt.figure(figsize=(10, 6))
        plt.bar(land_types, rmse_values, color="skyblue")
        plt.xlabel("地类", fontsize=16)
        plt.ylabel("RMSE_original", fontsize=16)
        plt.title("不同地类的RMSE_original", fontsize=18)
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "rmse_original.png"), dpi=300)
        plt.show()

    def plot_heatmap(self, data, key, title, filename):
        """
        绘制热力图
        :param data: 加载的地类数据
        :param key: 数据键（rmse_noise 或 contribution）
        :param title: 图标题
        :param filename: 输出文件名
        """
        # 确保 values 数据维度与因子数量和地类数量一致
        values = np.array([d[key] for d in data]).T  # 转置矩阵，将因子作为行，地类作为列
        if values.shape != (len(self.factors), len(self.land_types)):
            raise ValueError(f"热力图数据维度不匹配！预期 {len(self.factors)} x {len(self.land_types)}，但得到 {values.shape}。")
    
        fig, ax = plt.subplots(figsize=(12, 8))
        im = ax.imshow(values, cmap="YlGnBu", aspect="auto")
    
        # 设置坐标轴
        ax.set_xticks(np.arange(len(self.land_types)))
        ax.set_yticks(np.arange(len(self.factors)))
        ax.set_xticklabels(self.land_types, fontsize=14)
        ax.set_yticklabels(self.factors, fontsize=14)
        ax.set_xlabel("地类", fontsize=16)
        ax.set_ylabel("因子", fontsize=16)
        ax.set_title(title, fontsize=18)
    
        # 在格网内部写数值
        norm = plt.Normalize(vmin=values.min(), vmax=values.max())  # 归一化，用于颜色判断
        for i in range(values.shape[0]):  # 因子作为行
            for j in range(values.shape[1]):  # 地类作为列
                text = f"{values[i, j]:.3f}"
                # 根据颜色深浅动态调整数字颜色
                color = "white" if norm(values[i, j]) > 0.5 else "black"
                ax.text(j, i, text, ha="center", va="center", fontsize=12, color=color)
    
        # 添加颜色条
        cbar = fig.colorbar(im, ax=ax)
        cbar.ax.tick_params(labelsize=14)
        cbar.set_label("值", fontsize=16)
    
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=300)
        plt.show()

    def visualize(self):
        """
        执行所有可视化任务
        """
        data = self._load_data()
        self.plot_rmse_original(data)
        self.plot_heatmap(data, key="rmse_noise", title="不同地类的RMSE_noise热力图", filename="rmse_noise_heatmap.png")
        self.plot_heatmap(data, key="contribution", title="不同地类的贡献度热力图", filename="contribution_heatmap.png")


if __name__ == "__main__":
    csv_dir = r"F:\landuse\data\unsignedchar\homework\contribution"
    output_dir = r"F:\landuse\data\unsignedchar\homework"

    visualizer = ContributionVisualizer(csv_dir, output_dir)
    visualizer.visualize()