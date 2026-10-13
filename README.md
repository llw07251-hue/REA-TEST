# REA-TEST

[REA](https://rea.tools/) ([morluto/rea](https://github.com/morluto/rea)) 설치 및 테스트용 저장소입니다.

## 포함된 설정

- `.mcp.json` — Claude Code 프로젝트 범위 MCP 등록. `npx -y rea-agents@6.4.0 mcp`로 REA MCP 서버(도구 170개)를 실행합니다.
- `.claude/skills/reverse-engineer-anything/` — `rea setup`이 설치하는 REA 6.4.0 워크플로 스킬 사본.

이 저장소를 Claude Code로 열면 별도 설치 없이 REA MCP 서버와 스킬을 사용할 수 있습니다
(프로젝트 MCP 서버는 처음 사용할 때 승인 필요). 요구 사항: Node.js 22.x(>=22.19), 24.x(>=24.11) 또는 26+.

## 로컬 전역 설치 (선택)

```bash
npm install --global rea-agents@6.4.0     # Linux 설치 스크립트는 --prefix ~/.local 사용
rea setup --client claude_code --yes      # ~/.claude.json 등록 + 개인 스킬 설치
rea doctor                                # 준비 상태 확인
```

네이티브 바이너리 분석에는 Hopper, Ghidra(`GHIDRA_INSTALL_DIR`) 또는 IDA가 별도로 필요합니다.
JavaScript/Electron, .NET, 웹사이트 등 정적 분석은 엔진 없이 동작합니다.

## 업데이트

```bash
npx rea-agents@latest setup
```

업데이트 후 `.mcp.json`의 버전과 `.claude/skills/` 사본도 함께 갱신하세요.
