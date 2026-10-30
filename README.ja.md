# APDO — DOOM on KWS-X1

[English](README.md) · [日本語](README.ja.md)

**KOWSI KWS-X1の本体でDOOMが動きました。** 省メモリ版DOOMエンジンでFreedoomのE1M1を実行し、HC32F460でゲーム処理と描画を行います。本体に収まらない素材はUSB接続したPCから供給します。

**プレイ中もPCへの接続が必要です。** v4ではブラウザーからのキーボード／画面ボタン操作と、実機画面の低頻度プレビューに対応しました。本体ボタンも引き続き使えます。

## 実機確認

| 項目 | 結果 |
| --- | --- |
| 実機 | KOWSI KWS-X1の1台、Bootloader V1.1 |
| 実行環境 | Cortex-M4 / HC32F460、公称192MHzの設定 |
| ゲーム | Freedoom 0.13.0、E1M1 |
| 表示 | 240×135液晶の中央に180×135、ゲーム全体を4:3で表示 |
| 操作 | 移動・旋回・射撃・扉／スイッチ・メニューを確認 |
| v3の速度 | 開始場面の中央値180ms／フレーム、**約5.6fps** |
| USB | CDCで素材供給。長さ・連番・位置・CRC32を照合 |
| PC接続（v4） | ローカルAPI経由で入力・短押し・自動解除・映像停止／再開・画像取得を実機確認 |
| 更新 | v2/v3/v4でローダーの最終受け入れとフラッシャー終了コード0を確認 |
| 純正への復旧 | 純正更新ファイルの形式は検査済み。**復元の実機確認は未実施** |

v2の初期測定は1フレーム1,174ms・USB待ち669ms、v3は180ms・USB待ち4msでした。同じ開始場面の測定で約**6.5倍**に改善しています。場所や未取得の素材によって速度は変わります。測定数と確認範囲は[検証記録（英語）](docs/VALIDATION.md)を参照してください。

音声、セーブ、ゲーム設定の永続保存、別マップへの遷移は対応範囲外です。測定・PD・QCのタスクは起動しません。PCのデータ対応USBで接続し、他の機器は接続しない構成です。

[本体完結版の容量調査（英語）](docs/STANDALONE-FEASIBILITY.md)では、縮小したE1M1素材と内蔵フラッシュの容量を実測しています。小型の専用マップで単体動作を目指す案で、実装はまだ行っていません。

## 本体操作

| 動作 | ボタン |
| --- | --- |
| 前進 | OK |
| 旋回 | 左／右 |
| 射撃 | Back |
| 扉・スイッチ | 左＋右 |
| メニューを開く | OK＋Back |
| メニューの上下 | 左／右 |
| 決定／戻る | OK／Back |
| 純正更新ローダーへ入る | Back＋OKを押しながらUSB接続 |

ボタンは5msごとに読み取り、チャタリングを除去します。描画が遅い場面でも短い押下を残すため、上限付きの入力キューを使います。

## PCからプレイする（v4）

v4をビルドして本体へ導入後、次を起動します。

```powershell
.\scripts\play.ps1
```

サーバーを起動したまま、表示されたローカルURLを開きます。**Enable keyboard**を押すと次のキーが使えます。

| 動作 | PC入力 |
| --- | --- |
| 前進／後退 | W／S、または上／下 |
| 左右旋回 | A／D、または左／右 |
| 射撃 | Space、またはCtrl |
| 扉・スイッチ | E |
| メニュー／決定 | Esc／Enter |

画面上のボタンもマウスやタッチで押し続けられます。**Release all**は素材供給を続けながらPC入力を解除します。別ウィンドウやタブへ移るとキーを解除し、キーボード操作を無効にします。戻ったら**Enable keyboard**を押してください。

プレビューは実機の画面を**120×90、最大毎秒1回**で取得します。本体の描画速度とは別です。速度を優先するときは**Live preview**をオフにできます。**Save frame**で最新のBMPを保存できます。画面のMeter FPSは映像転送の待ち時間を含みます。上記v3の速度は過去の別測定です。

操作サーバーが素材供給も担当するため、他の素材サーバーは先に終了してください。自動認識はv4のシリアル文字列`KWSX1DOOM04`を対象にします。旧版ファームは更新が必要です。起動時には`-NoBrowser`、`-Port 8080`、`-UsbPort COM6`も指定できます。**Stop server**は素材供給も終了するので、再開にはサーバーの再起動と本体の電源入れ直しが必要です。詳細と確認範囲は[PC操作・通信仕様（英語）](docs/PC-CONTROLS.md)を参照してください。

## ソースとビルド

検証した環境は**Windows、PowerShell、Python 3.12、RustのWindows GNUツールチェーン、LLVM-MinGW**です。他の環境は未検証です。[ビルド手順（英語）](docs/BUILD.md)に従ってツールと必要に応じた個人設定を用意し、次を実行します。

```powershell
git clone https://github.com/inuchanbt/apdo-doom-on-kws-x1.git
cd apdo-doom-on-kws-x1
. .\scripts\env.ps1
& $env:KWS_PYTHON -m pip install -r requirements.txt
& $env:KWS_PYTHON scripts\prepare-sources.py
.\scripts\prepare-data.ps1
.\scripts\build.ps1 -Name kws-x1-doom
```

ソースと素材のハッシュは[SOURCE_LOCK.json](SOURCE_LOCK.json)、Rust依存は[locks/board.Cargo.lock](locks/board.Cargo.lock)に固定しています。ソース準備は競合する編集を上書きしません。変換器はFreedoomの固定リリースを取得して照合します。検証済みZIPを手元のキャッシュから指定することもできます。

**ここまでのコマンドはUSBを開かず、実機へ書き込みません。** X1Cを生成し、展開後の全バイト・消去範囲・オフラインの書き込み計画を検査します。実機更新前に[更新・復旧手順（英語）](docs/RECOVERY.md)を確認してください。本リポジトリはソース公開用で、汎用インストーラーではありません。

## 画面なしの素材サーバー・旧版ファーム

v4でブラウザー操作と映像を使わない場合は、操作サーバーの代わりに次を起動します。

```powershell
. .\scripts\env.ps1
& $env:KWS_PYTHON scripts\serve-game.py --auto --version 4
```

自動認識は、この移植の開発用USB識別情報とシリアル文字列が一致するポートだけを選びます。複数台ある場合は、実際の番号で`--port COM5`のように指定します。プレイ中は素材サーバーを1個起動したままにしてください。このサーバーにファーム書き込み機能はありません。

フレーム時間、USB待ち、素材要求数、入力状態、展開回数、スタックの未使用量を`artifacts/runtime.jsonl`へ記録します。ブラウザー操作サーバーの既定は`artifacts/runtime-v4.jsonl`です。どちらもPythonから直接起動すれば`--stats artifacts/run.jsonl`で保存先を変更できます。v1/v2/v3では、画面なしの素材サーバーに対応する`--version`を指定します。

切断、応答の破損、読み出しのタイムアウトでは停止します。再開にはサーバーの再起動と本体の電源入れ直しが必要です。プレイ中の自動再接続は未実装です。

## 構成

- [KM003C版](https://github.com/inuchanbt/apdo-doom-on-km003c)と同じ省メモリエンジン接続部分を使用します。
- 基板初期化、液晶・DMA、純正ローダー経由の更新形式と展開器は[kralonur/kws-x1-standalone-rs](https://github.com/kralonur/kws-x1-standalone-rs)を基にしています。
- よく使うFreedoomの179ページを圧縮後122,863バイトで既存の上側アプリ領域へ格納し、残りはUSBでLZ4転送します。
- 8KiBの展開済みキャッシュと32KiBの圧縮LRUキャッシュを併用します。画面は180×135のゲーム部分だけ保持し、左右の黒帯には画面メモリを割り当てません。
- 更新ファイルでは、展開中に未読の圧縮データを消さない配置を計算し、本体と同じ復号処理で全バイトを照合します。
- v4では同じUSB CDC接続で素材・有効期限付き入力・状態通知・任意の映像取得を扱います。描画済み画面を小分けに読み出すため、2枚目の画面メモリは不要です。

## フォルダー構成

| パス | 内容 |
| --- | --- |
| `native/` | Cエンジン接続部分とPC検証用ハーネス |
| `overlays/firmware/` | KWS-X1向け追加ソースと許諾済みFreedoom素材の抜粋 |
| `patches/` | 固定した上流ソースへの変更 |
| `locks/` | Rust依存の固定情報 |
| `scripts/` | ソース・素材準備、ビルド、検証、計測、PC操作・素材サーバー |
| `web/` | ローカルの操作画面と実機プレビュー |
| `tests/` | エンジン、通信、復号器、キャッシュの検査 |
| `docs/` | ビルド・復旧・検証記録（英語） |
| `notices/` | 上流ライセンスとFreedoomクレジット |
| `config/` | 個人用ツール設定の例 |
| `vendor/`, `tools/` | ローカルの依存ソースとツール、Git対象外 |
| `local/`, `firmware/`, `artifacts/`, `backups/` | 個人設定、メーカー配布物、生成物、実機記録、Git対象外 |

## 謝辞・ライセンス

KWS-X1ファームとHC32 HALの作者、[DMC100-Doom](https://github.com/ArturBieniek4/DMC100-Doom)、[doomgeneric](https://github.com/ozkl/doomgeneric)、id Software、[Freedoom](https://freedoom.github.io/)に感謝します。

個別の指定がない資料には既存の[MITライセンス](LICENSE)を維持します。エンジン接続部分と`GPL-2.0-or-later`表記のファイルには[COPYING](COPYING)を適用します。同梱したFreedoomの抜粋は独自のBSDライセンスです。有償DOOMのIWADやメーカー製ファームは同梱しません。上流の条件は引き続き適用されます。範囲と出典は[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)を参照してください。
