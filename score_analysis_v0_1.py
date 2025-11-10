# score_analysis_v0_1.py 的符号链接模块
# 这个文件用于让 app.py 能够导入 score_analysis_v0.1.py 中的函数

import sys
import importlib.util

# 动态导入 score_analysis_v0.1.py
spec = importlib.util.spec_from_file_location("score_analysis_module", "score_analysis_v0.1.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# 导出所有需要的函数
read_config = module.read_config
progress_score = module.progress_score
ranking_bonus = module.ranking_bonus
chain_bonus_score = module.chain_bonus_score
total_score_bonus = module.total_score_bonus
detect_subject_bias = module.detect_subject_bias
bias_penalty_score = module.bias_penalty_score
