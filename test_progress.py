# 测试 progress_score 函数逻辑（修复后）

def progress_score(before, now, weights):
    if before == 0 or now == 0 or now >= before:
        return 0.0
    score = 0.0
    # 从 now+1 开始，不包括当前排名now
    for r in range(now + 1, before + 1):
        for start, end, w in weights:
            if start <= r <= end:
                score += w
                break
    return score

# 实际配置（从截图）
weights = [
    (0, 20, 2.0),
    (21, 50, 1.8),
    (51, 100, 1.5),
    (101, 150, 1.2),
    (151, 200, 1.0),
    (201, 300, 0.8),
    (301, 430, 0.6)
]

print("=" * 80)
print("修复后测试")
print("=" * 80)

print("\n测试用例 1: 44→34 (进步10名)")
result1 = progress_score(44, 34, weights)
print(f"  期望: 10名 × 1.8 = 18.0")
print(f"  实际: {result1:.1f}")
print(f"  {'✅ 正确' if abs(result1 - 18.0) < 0.1 else '❌ 错误'}")

print("\n测试用例 2: 34→25 (进步9名)")
result2 = progress_score(34, 25, weights)
print(f"  期望: 9名 × 1.8 = 16.2")
print(f"  实际: {result2:.1f}")
print(f"  {'✅ 正确' if abs(result2 - 16.2) < 0.1 else '❌ 错误'}")

print("\n测试用例 3: 46→44 (进步2名)")
result3 = progress_score(46, 44, weights)
print(f"  期望: 2名 × 1.8 = 3.6")
print(f"  实际: {result3:.1f}")
print(f"  {'✅ 正确' if abs(result3 - 3.6) < 0.1 else '❌ 错误'}")

print("\n测试用例 4: 25→15 (跨区间进步)")
result4 = progress_score(25, 15, weights)
print(f"  16-20名: 5名 × 2.0 = 10.0")
print(f"  21-25名: 5名 × 1.8 = 9.0")
print(f"  期望总计: 19.0")
print(f"  实际: {result4:.1f}")
print(f"  {'✅ 正确' if abs(result4 - 19.0) < 0.1 else '❌ 错误'}")

