from yikd_web_client import AppSettingsModel, LoginType, YiK3CloudClient


def main() -> None:
    settings = AppSettingsModel("YiKdWebCfg/appsettings.xml")
    with YiK3CloudClient() as client:
        client.AppSettingsModel = settings
        client.LoginType = LoginType.LoginBySignSHA256
        print(client.View("BD_MATERIAL", '{"Number":"PRE001"}'))


if __name__ == "__main__":
    main()
