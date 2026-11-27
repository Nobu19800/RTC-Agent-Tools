# Lua RTC の静的解析と単体テスト

[English](en/lua-rtc-checks.md)

`TimedLongLimiter` は `RTC::TimedLong` を受け、値を −100 から 100 の範囲に収めて同じ型で出力します。入力のタイムスタンプを引き継ぎます。接続例は `ConsoleIn.out → TimedLongLimiter.in → TimedLongLimiter.out → ConsoleOut.in` です。ポート型はすべて同じなので、標準の DataPort 通信で接続できます。

> Lua の TimedLongLimiter に Luacheck を実行し、LuaUnit の単体テストと LuaCov のカバレッジを表示して。

エージェントが Ubuntu または WSL2 の Bash で実行する例です。Lua 5.1 と LuaRocks を用意します。RTC 自体を起動する場合は、AGENTS.md の RTM-Lua 導入手順に従います。

```bash
# Lua 5.1 用のツールを同じ LuaRocks のツリーに導入
luarocks --lua-version=5.1 --local install luacheck
luarocks --lua-version=5.1 --local install luaunit
luarocks --lua-version=5.1 --local install luacov
eval "$(luarocks --lua-version=5.1 --local path)"

# RTC-Agent-Tools のルートから実行
src="$(realpath examples/lua-rtc-checks)"
luacheck --std lua51 "$src/TimedLongLimiter.lua" "$src/limit.lua" "$src/test_limit.lua"

# 前回のカバレッジを混ぜないよう、新しい作業領域で計測
run="$(mktemp -d)"
cp "$src/.luacov" "$run/"
(
    cd "$run"
    export LUA_PATH="$src/?.lua;${LUA_PATH:-;}"
    lua5.1 -lluacov "$src/test_limit.lua"
    luacov
    cat luacov.report.out
)
```

## 2026-11-27 の実行結果

| 検査 | 結果 |
| --- | --- |
| Luacheck | 3 ファイル、警告 0 件、エラー 0 件 |
| LuaUnit | 3 件成功、失敗 0 件 |
| LuaCov | `limit.lua` の実行可能行 8/8（100%） |

LuaUnit では上下限を超えた場合と、境界を含む範囲内の値を確認しました。計測対象は値を制限する処理です。検証には、Ubuntu パッケージから展開した Lua 5.1 と LuaUnit、および上流ソースの Luacheck と LuaCov を使いました。

## Windows と WSL2 での RTC 間通信

> ConsoleIn、TimedLongLimiter、ConsoleOut を起動して接続し、範囲外の値が −100〜100 に制限されることを確認して。

エージェントが次の手順を実行します。両環境の互換性対策は [AGENTS.md](../AGENTS.md#openrtm-lua-rtm-lua) を参照してください。

1. **Windows** では公式の RTM-Lua 0.5.0 x64・Lua 5.1・`corba_cdr` 対応版を展開します。配布版の `examples` から、`LUA_PATH=..\lua\?.lua;.\?.lua;` と `LUA_CPATH=..\clibs\?.dll;` を設定し、3 本をそれぞれ `..\bin\lua.exe <RTC>.lua -f <RTC>.conf` で起動します。Limiter のソース 2 本をその作業フォルダに置きます。ログへリダイレクトする場合は `-e 'io.stdout:setvbuf("no")'` をスクリプト名の前に追加できます。
2. **WSL2** では RTM-Lua 0.5-3 を Lua 5.1 用のユーザーツリーに入れます。今回の配布 Rock は展開できなかったため、公式ソースの rockspec を使用しました。UUID を `0.2-1` に固定し、そのツリーと Limiter のソースディレクトリを Lua の検索パスに加えます。上流の `examples` を作業ディレクトリとし、`lua5.1 <スクリプトのパス> -f <RTC>.conf` でそれぞれ起動します。
3. 各 `rtc.conf` に、到達できる共有ネームサーバーと固有の CORBA エンドポイントを設定します。今回の Windows は `127.0.0.1:2809`、WSL2 は Windows 側の WSL ゲートウェイの `:2809` を使用しました。各 RTC に `2821`〜`2823` の異なるポートを割り当て、`naming.formats: %n.rtc` を使いました。
4. 登録後、`ConsoleIn0.out → TimedLongLimiter0.in` と `TimedLongLimiter0.out → ConsoleOut0.in` を接続します。今回の検証では `PortService.connect` に `corba_cdr`、`push`、`flush` を指定しました。ConsoleOut、Limiter、ConsoleIn の順で活性化し、整数を入力します。
5. ConsoleOut の受信ログを照合し、3 つの RTC を停止します。共有ネームサーバーは稼働を続けます。

| 環境 | ConsoleIn の入力 | ConsoleOut の受信 |
| --- | --- | --- |
| Windows ネイティブ | −250, −100, 0, 42, 100, 250 | −100, −100, 0, 42, 100, 100 |
| WSL2 Ubuntu | −250, −100, 0, 42, 100, 250 | −100, −100, 0, 42, 100, 100 |
