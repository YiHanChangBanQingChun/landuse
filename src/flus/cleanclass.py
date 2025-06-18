def clean_class(fclass_value):
    if fclass_value is None:  # 处理空值
        return None
    if '_' in fclass_value:   # 检查是否包含下划线
        return fclass_value.split('_')[0]  # 分割后取第一部分
    else:
        return fclass_value  # 无下划线则返回原字符串