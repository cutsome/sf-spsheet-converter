import sys
from typing import Optional


class StackProps:
    """
    Stack 共通の変数をまとめている
    """

    def __init__(
        self,
        account: Optional[str] = None,
        region: Optional[str] = None,
        system_name: Optional[str] = None,
        service_name: Optional[str] = None,
        function_name: Optional[str] = None,
    ) -> None:

        """パラメータ"""

        if not account:
            print("Please enter a value for ACCOUNT in .env")
            sys.exit(1)
        else:
            self.__account = account

        if not region:
            print("Please enter a value for REGION in .env")
            sys.exit(1)
        else:
            self.__region = region

        if not service_name:
            print("Please enter a value for SERVICE_NAME in .env")
            sys.exit(1)
        else:
            self.__service_name = service_name

        if not system_name:
            print("Please enter a value for SYSTEM_NAME in .env")
            sys.exit(1)
        else:
            self.__system_name = system_name

        if not service_name:
            print("Please enter a value for SERVICE_NAME in .env")
            sys.exit(1)
        else:
            self.__service_name = service_name

        if not function_name:
            print("Please enter a value for FUNCTION_NAME in .env")
            sys.exit(1)
        else:
            self.__function_name = function_name

    @property
    def account(self) -> str:
        return self.__account

    @property
    def region(self) -> str:
        return self.__region

    @property
    def system_name(self) -> str:
        return self.__system_name

    @property
    def service_name(self) -> str:
        return self.__service_name

    @property
    def function_name(self) -> str:
        return self.__function_name
