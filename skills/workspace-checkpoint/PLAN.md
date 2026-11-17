# Workspace Checkpoint 实施计划

**目标**：实现通用的 `workspace-checkpoint`，用只读辅助检查、项目活记忆和保守的本地提交流程完成工作收尾。

**架构**：`SKILL.md` 驱动 AI 的判断与执行；Python 标准库脚本只收集证据，不删除、不提交。模板与项目路径适配保证不同仓库可用。

**技术栈**：Markdown、Python 3、Git、pytest。

**设计依据**：同目录 `DESIGN.md`。

## 全局约束

- 脚本只读，不自动总结、删除、stash、提交或 push。
- 只提交本任务文件；代码与记忆分开提交，不默认添加协作署名。
- 项目记忆保留最近 30 天摘要，稳定规则提炼去重。
- 禁止默认 `git clean -fdx`，不明文件保留。

## 审查重点

- 非 Git 目录返回文件信息快照，不伪造 Git 状态。
- 带空格和中文的路径使用 `pathlib` 与参数数组。
- 使用 NUL 分隔的 Git 状态，区分暂存、未暂存和 rename。
- 没有 `docs/` 的项目使用根目录 `AI_MEMORY.md`。
- `out/`、共享缓存和宿主配置不得成为清理候选。

## 任务 1：只读工作区检查器

文件：

- `scripts/audit_workspace.py`
- `tests/test_audit_workspace.py`

接口：

- `choose_memory_path(root: Path) -> Path`
- `parse_git_status(text: str) -> list[dict]`
- `is_regenerable_cache(path: Path) -> bool`
- `audit_workspace(root: Path) -> dict`

步骤：

1. 先写路径适配、状态解析、保护目录、非 Git 和空仓库测试，确认因实现缺失而失败。
2. 实现只读检查器，收集分支、状态、最近提交、记忆路径建议和缓存候选。
3. 运行 `python -m pytest tests -q`，确认全部通过。
4. 在目标项目运行 `python scripts/audit_workspace.py --root <project-root> --json`，核对输出且不产生修改。

## 任务 2：Skill 流程与模板

文件：

- `SKILL.md`
- `assets/ai-memory-template.md`

步骤：

1. 按设计写执行顺序、停止条件和脱敏要求。
2. 用消费者代理干跑验证行为，不使用源文本 grep 代替行为验收。
3. 运行 `python -m pytest tests -q`，确认全部通过。

## 任务 3：目标项目首次实跑

1. 遵循目标项目分支规则；有不明代码改动时保留，不纳入文档提交。
2. 从近期提交和现有文档生成项目记忆，按宿主能力同步持久记忆摘要。
3. 检查文档链接和 `git diff --check`，只清理本轮可再生缓存。
4. 精确暂存项目记忆和索引，确认暂存范围后用独立 `docs:` 提交。
5. 报告测试证据、提交哈希、清理项和保留项。
