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

## Test

Actions

```
{
  "siteId": "676539db-c5cf-6c90-49b7-cd9c40a9985d",
  "action": "createNewService",
  "serviceType": "edit-wordpress",
  "phpVersion": "7.0",
  "fsId": "fs-4691580f"
}
```

```
{
  "siteId": "676539db-c5cf-6c90-49b7-cd9c40a9985d",
  "action": "deleteTheService"
}
```


```
{
  "siteId": "676539db-c5cf-6c90-49b7-cd9c40a9985d",
  "action": "syncEfsToS3",
  "serviceType": "edit-wordpress",
  "phpVersion": "7.0",
  "fsId": "fs-4691580f"
}
```

```
{
  "siteId": "001bbf96-31dd-6528-7a0f-84e3710b0738",
  "action": "syncEfsToS3",
  "fsId": "fs-88d311c1"
}
```

```
{
  "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
  "action": "createNewService",
  "serviceType": "edit-wordpress",
  "phpVersion": "5.5",
  "fsId": "fs-5286491b"
}
```


```
{
  "siteId": "global-dd-agent-worker",
  "action": "getTheService"
}
```