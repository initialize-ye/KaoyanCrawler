# 贡献指南

感谢你对KaoyanCrawler的兴趣！

## 如何贡献

### 添加新学校配置

1. 在 `configs/` 目录下创建 `{学校拼音}.yaml`
2. 参考 `configs/template.yaml` 填写配置
3. 测试爬虫是否正常工作
4. 提交PR

### 报告问题

- 使用GitHub Issues报告bug
- 提供完整的错误日志和复现步骤

### 提交代码

1. Fork项目
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改
4. 推送到Fork
5. 创建Pull Request

## 开发规范

- Python代码遵循PEP 8
- 使用type hints
- 新功能需要附带测试
- 提交信息使用中文或英文均可，但要清晰描述改动
