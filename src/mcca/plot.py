import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np

def plot_landuse_trends(csv_path):
    """
    绘制土地覆盖类型随时间变化的折线图和方差变化图
    :param csv_path: CSV文件路径，包含真实数据和预测数据
    """
    # 设置中文字体支持
    rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
    rcParams['axes.unicode_minus'] = False   # 解决负号显示问题

    # 读取CSV文件
    data = pd.read_csv(csv_path)

    # 提取年份和类型数据
    years = data["Category"]
    types = data.columns[1:]
    real_years = years[:4]  # 前4年为真实数据
    predict_years = years[4:]  # 后续为预测数据

    # 定义线性回归方程
    regression_equations = {
        "Type1": lambda x: -0.00195312 * x + 4.284,
        "Type2": lambda x: -0.000361328 * x + 1.144,
        "Type3": lambda x: -9.69238e-05 * x + 0.248,
        "Type4": lambda x: 0.000869141 * x - 1.627,
        "Type5": lambda x: 0.00151489 * x - 3.02325,
        "Type6": lambda x: 4.89502e-05 * x - 0.07725,
        "Type7": lambda x: -2.30408e-05 * x + 0.0514375,
    }

    # 定义土地类型名称
    land_type_names = {
        "Type1": "田地",
        "Type2": "林地",
        "Type3": "草原",
        "Type4": "水体",
        "Type5": "城市用地",
        "Type6": "农村住区",
        "Type7": "其他",
    }

    # 创建图形
    fig, axes = plt.subplots(2, 4, figsize=(16, 10))
    axes = axes.flatten()

    # 绘制每种类型的折线图
    for i, land_type in enumerate(types):
        ax = axes[i]
        # 绘制预测值的点，保持蓝色
        ax.plot(years, data[land_type], label="真实与预测数据", marker="o", color="blue")
        # 绘制真实值的点，设置为绿色
        ax.plot(real_years, data[land_type][:4], label="真实数据", marker="o", color="orange")
        # 绘制线性回归预测，保持红色
        ax.plot(predict_years, [regression_equations[land_type](x) for x in predict_years], 
                label="线性回归预测", linestyle="--", color="red")
        ax.set_title(f"{land_type_names[land_type]} 土地类型随时间变化", fontsize=12)  # 使用正确的土地类型名称
        ax.set_xlabel("年份")
        ax.set_ylabel("覆盖比例")
        ax.legend()
        ax.grid()

    # 计算方差并绘制方差变化图
    variances = data[types].var(axis=1)
    ax = axes[-1]
    ax.plot(years, variances, label="方差随时间变化", marker="o", color="green")
    ax.set_title("土地覆盖类型方差随时间变化", fontsize=12)
    ax.set_xlabel("年份")
    ax.set_ylabel("方差")
    ax.legend()
    ax.grid()

    # 调整布局并保存图片
    plt.tight_layout()
    output_path = csv_path.replace(".csv", "_土地覆盖变化图.png")
    plt.savefig(output_path, dpi=300)
    plt.show()

if __name__ == "__main__":
    csv_path = r"F:\landuse\data\double\futurepredict.csv"
    # plot_landuse_trends(csv_path)