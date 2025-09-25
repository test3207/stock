import json

# 读取HS300成分股
with open('data/raw/index_members_000300.json') as f:
    hs300_data = json.load(f)
print(f'HS300 symbols count: {len(hs300_data["symbols"])}')

# 读取CSI500成分股  
with open('data/raw/index_members_000905.json') as f:
    csi500_data = json.load(f)
print(f'CSI500 symbols count: {len(csi500_data["symbols"])}')

# 合并去重统计
all_symbols = set(hs300_data["symbols"]) | set(csi500_data["symbols"])
print(f'Total unique symbols: {len(all_symbols)}')

# 重叠统计
overlap = set(hs300_data["symbols"]) & set(csi500_data["symbols"])
print(f'Overlap between HS300 and CSI500: {len(overlap)}')