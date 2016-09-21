# iPythonでいろいろテスト

とりあえずコンフィグを読む

```
import json
import yaml
import sys
import os
import logging
config_base = yaml.load(open('./config/appconfig.yml', 'r'))
app_config = config_base['development']

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

```

ライブラリ内のクラスをロードしてつかってみる。

```
from mylibs.ServiceBuilder import *
svc = ServiceBuilder()
```

プライベートの関数には `インスタンス._クラス名__変数名`で無理やりアクセスできる。

```
svc._ServiceBuilder__getSyncEfsToS3ImageBody()

TypeError: __getSyncEfsToS3ImageBody() takes exactly 2 arguments (1 given)
```
