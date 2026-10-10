# Linux 開發環境 bootstrap

把 basic-pc 的慣用命令列環境帶到新的 Linux 主機。預設透過 sudo 安裝系統工具，uv、Node／Codex 與 shell 設定放在使用者目錄；保留既有工具和設定。腳本不複製帳號認證，也不假設新主機是 basic-pc 或共用 NFS。

## basic-pc 的實際設定

2026-10-10 從 basic-pc 唯讀盤點：

| 項目 | 現有設定 | 本腳本處理 |
| --- | --- | --- |
| 系統 | Ubuntu 26.04.1 LTS | 主要目標為 Ubuntu/Debian；另提供 dnf 套件選項 |
| Shell | Bash 5.3.9；Ubuntu 原本的 prompt／aliases | 保留原設定，不切換 shell |
| 命令列編輯 | ble.sh `0.4.0-devel4+d81fd54f` | 已有就重用；新安裝用上游 nightly 套件 |
| Python 工作流程 | uv 0.12.23；系統 Python 3.14.4 | 安裝缺少的 uv；Python 版本由各專案選擇 |
| Node | nvm 0.40.8；Node 24.21.0；npm 11.19.0 | 新安裝 nvm 0.40.8、Node 24；保留已有 default alias |
| Codex CLI | 0.161.0；安裝在 nvm 的 Node 目錄 | 新安裝預設 0.161.0，已存在則重用 |
| 常用工具 | Git 2.53.0、tmux 3.6、rg 15.1.0、fd 10.3.0、rsync 3.4.1 | 預設透過 sudo 安裝缺少的系統工具 |
| 運算工具 | Docker 29.8.2、`/usr/local/cuda` | 不列入通用 bootstrap，依主機另行處理 |
| 專案環境 | `~/Projects/<project>`、專案自己的 `.venv` | 保留這個工作習慣，不建立共用 Python 環境 |

目前沒有自訂 tmux.conf、starship、zsh、fzf、bat、eza 或 direnv 設定。因此不把這些當成已存在的偏好。basic-pc 的 SSH reverse tunnel、GPU 驅動、CUDA、Docker 權限、桌面設定與實驗室主機資訊，不搬到新伺服器。npm/corepack 等現有版本記錄不代表所有新機器都要鎖死相同 patch。

## 一行安裝（主要入口）

`install.sh` 是獨立完整安裝器，內含 bootstrap、設定更新器及可選 AGENTS.md。新主機不需要先 clone，也不會再從 repo 下載其他檔案；安裝工具本身仍需要網路。

固定的短入口：

```bash
curl -fsSL https://jjjerryc.github.io/i | bash
```

沒有 curl、但有 wget 時：

```bash
wget -qO- https://jjjerryc.github.io/i | bash
```

短入口由你的 GitHub Pages 提供，會下載原 repository 的最新版安裝器，不需另外同步一份完整腳本。原始備援網址：`https://raw.githubusercontent.com/jjjerryc/linux-dev-bootstrap/main/install.sh`。

預設就是完整安裝：Ubuntu/Debian 使用 sudo apt，Fedora 使用 sudo dnf，包含 tmux、rg、fd、rsync、Git、zip／unzip、htop、nvtop 等系統工具，以及使用者目錄的 uv、ble.sh、Node／Codex。sudo 可能提示密碼；請用一般帳號執行，讓腳本只對系統套件呼叫 sudo。

共用伺服器沒有 sudo 權限時可改用：

```bash
curl -fsSL https://jjjerryc.github.io/i | bash -s -- --user-only
```

這個模式需管理員事先提供 Bash、curl、Python 3、Git、tar、xz 和 gawk。`--config-only` 只調整設定，不呼叫 sudo 或安裝工具。

其他選項同樣可以傳入：

```bash
curl -fsSL https://jjjerryc.github.io/i | bash -s -- --dry-run
curl -fsSL https://jjjerryc.github.io/i | bash -s -- --with-agents
```

安裝器有來源、版本選擇和設定備份，會重用已安裝的工具。完成後**開新終端**就能使用 ble.sh、uv、Node 和 Codex；安裝器無法修改呼叫它的既有 shell。Codex 仍需在新主機登入。入口也能放在任何可直接下載的 HTTPS 網址，不需要另開服務。

公開 repository：[jjjerryc/linux-dev-bootstrap](https://github.com/jjjerryc/linux-dev-bootstrap)。raw URL 可免登入下載。

### 本機／clone 方式

```bash
bash install.sh --dry-run
bash install.sh
# 開一個新的 Bash 終端
dev-doctor
```

完整模式預設使用 sudo 安裝依賴；單行下載入口只需已有 Bash、curl 及網路。`--user-only` 模式需主機已有必要依賴。腳本下載只用 HTTPS，下載到私人暫存目錄後執行。

```bash
bash bootstrap.sh               # 完整安裝（預設）
bash bootstrap.sh --user-only   # 使用者範圍，略過系統套件
```

只設定 shell，或調整安裝範圍：

```bash
bash bootstrap.sh --config-only
bash bootstrap.sh --no-codex
bash bootstrap.sh --no-node         # 同時略過 Codex
bash bootstrap.sh --node-version 24 --codex-version latest
bash bootstrap.sh --with-agents     # 新增可移植的 Codex 全域規則；既有規則完全保留
```

`--dry-run` 不下載、不寫檔、不呼叫 sudo。它顯示選項與整體計畫，實際相依性是否足夠仍由正式執行檢查。腳本只支援 Linux；Alpine/musl、NixOS、特殊受限環境並未驗證。Node 與 uv 的可用架構／glibc 要符合上游需求。

## 設定存放與重跑

- `~/.config/jayson-dev/env.sh`：只有 PATH 設定，可供非互動 shell 明確載入。
- `~/.config/jayson-dev/bash.sh`：互動 Bash 的 nvm、補全及 ble.sh 載入。
- `~/.bashrc`：只新增／更新 `linux-dev-bootstrap` 標記區塊。
- Login shell：已有 `.bash_profile` 或 `.bash_login` 就更新它，否則更新 `.profile`，不另外建立會遮蔽既有設定的 profile。
- `~/.local/bin/dev-doctor`：檢查硬體、工具版本及 shell 設定；`dev-doctor --json` 輸出結構化報告。
- `~/.local/share/jayson-dev/doctor.py`：標準函式庫實作，沒有額外 Python 套件依賴。
- `~/.local/bin/dev-run`：非互動命令的 PATH＋nvm 包裝器；用 `exec` 保留實際命令的退出碼。
- `~/.local/state/jayson-dev/backups/<時間戳>/`：修改前的設定備份；檔案私人權限。

重跑不會重複加入標記，不會升級已存在的 uv、ble.sh、nvm 或 Codex。Node 會重用指定版本範圍的已安裝版本；缺少時才安裝。這是「重建工作習慣」而非逐位元復刻：Node 24 新安裝的 patch、ble.sh nightly 會隨上游變動；如需嚴格版本鎖定，另外固定它們的完整版本／下載校驗值。新版使用者自行選擇更新，不會暗中重裝。

可保留原 shell 外觀；script 不修改 Git 使用者姓名／email、不登入 Codex/GitHub、不改 SSH、umask、系統服務或網路埠。Codex 登入在新主機自行完成，不能把原機的認證檔放進這個 repo。

## 遠端與專案使用

非互動 SSH 通常不載入 Bash 的互動設定。不要靠 `.bashrc` 的互動分支提供 Node：

```bash
ssh my-server '~/.local/bin/dev-run uv --version'
ssh my-server '~/.local/bin/dev-run codex --version'
ssh my-server '~/.local/bin/dev-run node --version'
```

Python 專案：

```bash
mkdir -p ~/Projects/example
cd ~/Projects/example
uv init
uv python pin 3.12       # 依專案需求選擇，這只是範例
uv add <套件>
uv run python <程式.py>
```

不搬 `.venv` 到另一台；搬程式碼和 `pyproject.toml`／`uv.lock` 後，在新機 `uv sync --locked`。已有工作在用同一環境時，先避免同步或升降套件。GPU 套件、CPU 工作數與運算啟動規則另外按主機決定。

可移植的 `config/AGENTS.md` 不含 basic-1/basic-2/basic-pc、24–32 workers、reverse tunnel、basictop 或 basic-pc 兩小時例外。這些是特定主機的規則，不應在陌生 Linux 主機自動生效。

## 驗證

```bash
python3 scripts/build_installer.py
bash -n install.sh bootstrap.sh doctor.sh
python3 -m unittest discover -s tests -v
bash bootstrap.sh --dry-run
```

測試使用暫存配置與假的下載／安裝命令，不改目前帳號的設定、不下載大型套件、不執行 sudo。這驗證安全的設定合併、重跑、現有工具重用與失敗處理；不代表每個 Linux 發行版上的實際網路安裝都已驗證。

## 上游來源

- [uv 安裝](https://docs.astral.sh/uv/getting-started/installation/)
- [nvm 安裝與 PROFILE=/dev/null](https://github.com/nvm-sh/nvm#installing-and-updating)
- [ble.sh 預編譯安裝](https://github.com/akinomyoga/ble.sh#quick-install)
- [Codex CLI 官方文件](https://learn.chatgpt.com/docs/codex/cli)

本目錄已整理成可以獨立發布的內容，未包含任何原機的認證或私有主機設定。公開發布於 https://github.com/jjjerryc/linux-dev-bootstrap 。

### 維護單行安裝器

修改 `bootstrap.sh`、`scripts/configure.py` 或 `config/AGENTS.md` 後執行 `python3 scripts/build_installer.py`，將產生的 `install.sh` 一起提交／發布。測試會確認它與來源一致，也會確認透過 stdin 執行時參數能正確傳遞、乾跑不會寫入使用者環境。

## 硬體盤點與自動驗證

安裝後自動執行 `dev-doctor`，驗證本次選擇安裝的工具及 managed shell 檔案的 Bash 語法；驗證失敗會以非零退出碼回報，不會假裝安裝成功。`--config-only` 不驗證未安裝工具。日後可直接執行：

```bash
dev-doctor
dev-doctor --json
dev-doctor --json > machine-report.json
```

報告包含 OS、kernel、架構、glibc、CPU 型號／邏輯 CPU 與目前可用執行槽、負載、RAM 總量與可用量、home 所在磁碟容量，以及 NVIDIA GPU 型號／VRAM／驅動版本。版本清單包含已安裝的核心開發工具，另檢查 gcc、g++、make、cmake、pkg-config、Docker、nvcc 與 nvidia-smi；後者是選用工具，這個腳本不因此安裝 CUDA、驅動、Docker 或所有編譯工具。

只讀取資訊，不跑 benchmark、不分配 GPU 工作、不下載模型、不掃描整個 home、不讀 SSH keys／token，也不自動上傳報告。GPU 查詢及工具版本命令有 timeout；無 NVIDIA GPU 的 CPU 主機仍可通過核心環境驗證。它不掃描每個專案 .venv 內的 PyTorch 等套件，專案依賴仍由各自的 lockfile 管理。

若之前已透過一行指令安裝，重跑同一行就會加入新的 doctor 與自動驗證，既有工具仍會重用。

預設也安裝 zip／unzip（壓縮解壓）、htop（CPU／程序監控）、nvtop（GPU 監控），並驗證各自的版本命令。nvtop 安裝不會順帶安裝或修復 GPU 驅動；CPU-only 主機不需要啟動 nvtop 的互動介面來通過版本驗證。
