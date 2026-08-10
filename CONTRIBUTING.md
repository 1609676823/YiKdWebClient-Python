# 参与贡献

本项目以 `D:\work\框架代码\YiKdWebClient` 对应的 C# 项目为行为基准，Java
项目用于交叉核对移植方式。修改公开 API 或服务路径时，请同步补充测试和
`docs/API_MAPPING.md`。

本地验证：

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
```

