def chain_bonus_score(chain_length, config):
    """
    根据连续进步次数计算加分
    只返回当前连续次数对应的奖励，不累加之前的
    """
    if chain_length == 0:
        return 0
    
    # 找到连续次数对应的奖励
    bonus = 0
    max_times = 0
    for times, b in config["chain_bonus"].items():
        if chain_length >= times and times > max_times:
            max_times = times
            bonus = b
    
    return bonus

# 测试
config = {
    "chain_bonus": {
        1: 5,
        2: 8,
        3: 12,
        4: 18,
        5: 25
    }
}

print("连续进步加分测试:")
print("=" * 50)
for i in range(6):
    bonus = chain_bonus_score(i, config)
    print(f"连续进步 {i} 次 → 加分: {bonus}")

print("\n" + "=" * 50)
print("验证:")
print("连续1次: 应该=5, 实际=" + str(chain_bonus_score(1, config)))
print("连续2次: 应该=8, 实际=" + str(chain_bonus_score(2, config)))
print("连续3次: 应该=12, 实际=" + str(chain_bonus_score(3, config)))
print("连续5次: 应该=25, 实际=" + str(chain_bonus_score(5, config)))
