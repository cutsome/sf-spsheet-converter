#%%
"""予実管理ダッシュボード自動生成スクリプト

以下のスプレッドシート「商談」「契約」シートに、
Salesforce から4時間おきにデータを同期している。

https://docs.google.com/spreadsheets/d/13WXWBeHL_nd0BYp98-L3S-eKrCjGsXd8lrBzPNWVMzs/edit#gid=2110653188

スプレッドシートを CSV を介さず Pandas で直接操作し、データを加工してグラフ化する。
プログラムはデータ整形のみ行い、グラフ化はスプレッドシートで行っている。
"""

import os
import logging
from pathlib import Path
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pandas as pd
import gspread
from dotenv import load_dotenv
from monthdelta import monthmod
from gspread import WorksheetNotFound
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe


def handler(event=None, context=None) -> None:

    ##############################
    # Configuration
    ##############################

    # カレントディレクトリ
    current_dir = Path(__file__).parent

    # ログ設定
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(levelname)s: %(asctime)s: %(name)s: %(message)s")
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.info("======= START =======")


    # 環境変数の読み込み
    dotenv_path = f"{current_dir.parent}/.env"
    load_dotenv(dotenv_path)


    # スプレッドシートの認証設定
    SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = f'{current_dir}/credentials.json'
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
    gs = gspread.authorize(credentials)
    SPREADSHEET_KEY = os.getenv("SP_KEY_1")
    workbook = gs.open_by_key(SPREADSHEET_KEY)


    today = date.today()
    start = date(2019, 4, 1)
    end: date = today.replace(day=1) + relativedelta(years=1)
    delta = monthmod(start, end)[0].months

    # 会計年度の算出
    def calc_fy(accounting_month: date, st: int = 2012):
        fy_start = date(st, 6, 1)
        fy_end = date(st+1, 5, 31)
        if fy_start <= accounting_month and accounting_month < fy_end:
            return st
        # 再帰
        return calc_fy(accounting_month, st+1)


    ##############################
    # 契約
    ##############################

    logger.info("======= 契約シート加工 START =======")
    worksheet = workbook.worksheet('契約(Auto)')
    df = pd.DataFrame(worksheet.get_all_values())


    """表整形"""
    df.columns = df.iloc[0]
    df.drop(
        index=df.index[[0]],
        columns=[
            'sno__c',
            'plan__c',
            'zentaiseitosu__c',
            'syoudan__c',
            'gyosyu__c',
        ],
        inplace=True
    )
    df = df.rename(
        columns={
            'Name': '教育機関名',
            'CreatedDate': '作成日',
            'OwnerId': '所有者',
            'kyoikukikanmei__c': '教育機関名Id',
            'donyuseitosu__c': '導入生徒数',
            'tanka__c': '単価',
            'keiyakukeitai__c': '契約形態',
            'keiyakukaisibi__c': '契約開始日',
            'status__c': 'ステータス',
            'stagename__c': 'フェーズ',
            'keiyakukoshinbi__c': '契約更新日',
        }
    ).astype(
        {
            '導入生徒数': 'int',
            '単価': 'int',
        }
    )


    """データ整形"""
    id2name = {
        'AAAA': 'aaaa',
        'BBBB': 'bbbb',
        'CCCC': 'cccc',
        'DDDD': 'dddd',
        'EEEE': 'eeee',
        'FFFF': 'ffff',
    }
    df['MRR'] = (df['導入生徒数'] * df['単価']).astype('int')
    df['所有者'] = df['所有者'].map(lambda x: id2name[x])
    df['契約形態'] = df['契約形態'].map(
        lambda x: x.replace('-','年契約') if x is not None else None
    )


    """売上計上処理

    Note:
        計上月:
            契約開始月 ~ 現在+1年後
            ※ 最古の計上月は 2019/4/1

        計上ステータス:
            現在以降の売上は「未確定」に、
            過去の売上は「確定」とする

            月契約:
                上記の期間、毎月 `MRR` (導入生徒数 * 単価) を計上する
            年契約:
                上記の期間、契約開始月から 1年ごとに `MRR` を計上する

    Variables:
        contracted_date: 契約開始日
        accounting_month: 計上月
    """

    df['計上月'] = ''
    df['計上ステータス'] = ''
    df['年度'] = 0

    logger.info("======= 契約シート 売上計上処理 START =======")
    for i, row in df.iterrows():
        contracted_date = datetime.strptime(row['契約開始日'], '%Y-%m-%d').date()

        # 月契約
        if row['契約形態'] == '月契約':
            for month in range(delta + 1):
                # 未来 -> 過去
                # 2023/1/1 - 0か月, 1か月, 2か月.....
                accounting_month = end - relativedelta(months=month)
                # 契約開始日より以前は計上しない
                if accounting_month < contracted_date.replace(day=1):
                    break
                row['計上月'] = accounting_month.strftime('%Y-%m')
                row['計上ステータス'] = (
                    '未確定'
                    if today.replace(day=1) < accounting_month
                    else '確定'
                )
                row['年度'] = calc_fy(
                    datetime.strptime(row['計上月'], '%Y-%m').date()
                )
                df = df.append(row.copy(), ignore_index=True)

        # 年契約
        elif row['契約形態'] == '年契約':
            for year in range(end.year, start.year, -1):
                # 2019/4/1, 2021/5/1   4 <= 5
                if start.month <= contracted_date.month:
                    year -= 1
                # 契約開始日より以前は計上しない
                if year < contracted_date.year:
                    break
                # 計上終了月(ex: 2023-01-01) < 計上月(ex: 2023-03-01)
                #   - 計上終了月が 4月以降の場合、処理をスキップする
                accounting_month = date(year, contracted_date.month, 1)
                if end < accounting_month:
                    continue
                row['計上月'] = accounting_month.strftime('%Y-%m')
                row['計上ステータス'] = (
                    '未確定'
                    if today.replace(day=1) < accounting_month
                    else '確定'
                )
                row['年度'] = calc_fy(
                    datetime.strptime(row['計上月'], '%Y-%m').date()
                )
                df = df.append(row.copy(), ignore_index=True)

    logger.info("======= 契約シート 売上計上処理 END =======")


    # 一部有料導入・全体有料導入の重複レコードを削除する
    df = df[df['計上月'] != '']
    df_keiyaku = df.loc[:1]
    for i in range(delta + 1):
        accounting_month = end - relativedelta(months=i)
        accounting_month = accounting_month.strftime('%Y-%m')
        try:
            # 計上月ごとに行分割
            tmp_df = df.groupby('計上月').get_group(accounting_month)
            # 一部有料導入・全体有料導入の両レコード間で、
            # 教育機関名Id が一致しているものは重複とする。
            #
            # keep='last' にすることで、一部有料導入の方を削除
            tmp_df = tmp_df[~tmp_df.duplicated(subset='教育機関名Id', keep='last')]
            # 行分割したものを再結合
            df_keiyaku = df_keiyaku.append(tmp_df)
        except:
            pass

    logger.info("======= 契約シート加工 END =======")


    ##############################
    # 商談
    ##############################

    logger.info("======= 商談シート加工 END =======")
    worksheet = workbook.worksheet('商談(Auto)')
    df = pd.DataFrame(worksheet.get_all_values())


    """表整形"""
    df.columns = df.iloc[0]
    df.drop(
        index=df.index[[0]],
        columns=[
            'sno__c',
            'gyousyu__c',
        ],
        inplace=True
    )
    df = df.rename(
        columns={
            'Name': '教育機関名',
            'OwnerId': '所有者',
            'AccountId': '教育機関名Id',
            'CreatedDate': '作成日',
            'dounyuyoteisu__c': '導入予定数',
            'souteitanka__c': '想定単価',
            'CloseDate': 'クローズ時期',
            'keiyakukeitai__c': '契約形態',
            'RecordTypeId': 'ステータス',
            'StageName': 'フェーズ',
            'kakudo__c': '確度',
        }
    ).astype({
        '導入予定数': 'int',
        '想定単価': 'int',
        '確度': 'int',
    })


    """データ整形"""
    id2name = {
        'AAAA': 'aaaa',
        'BBBB': 'bbbb',
        'CCCC': 'cccc',
        'DDDD': 'dddd',
        'EEEE': 'eeee',
        'FFFF': 'ffff',
    }
    id2status = {
        '0125h000000Z9LBAA0': '一部有料導入',
        '0125h000000Z9LGAA0': '全体有料導入',
    }
    df['MRR'] = (df['導入予定数'] * df['想定単価'] * df['確度'].map(lambda x: x / 100)).astype('int')
    df['所有者'] = df['所有者'].map(lambda x: id2name[x])
    df['ステータス'] = df['ステータス'].map(lambda x: id2status[x])
    df['契約形態'] = df['契約形態'].map(
        lambda x: x.replace('-','年') if x is not None else None
    )


    """売上計上処理

    Note:
        計上月:
            クローズ時期 ~ 現在+1年後

        計上ステータス:
            すべて「受注予定」に。

            月契約:
                上記の期間、毎月 `MRR` (導入予定数 * 想定単価 * 確度) を計上する
            年契約:
                上記の期間、クローズ時期から 1年ごとに `MRR` を計上する

    Variables:
        close_date: クローズ時期
        accounting_month: 計上月
    """

    df['計上月'] = ''
    df['計上ステータス'] = ''
    df['年度'] = 0

    logger.info("======= 商談シート 売上計上処理 START =======")
    for i, row in df.iterrows():
        close_date = datetime.strptime(row['クローズ時期'], '%Y-%m-%d').date()
        # クローズ時期が1年後以降の場合は、計上しない
        if end < close_date:
            break
        _delta = monthmod(close_date, end)[0].months

        # 月契約
        if row['契約形態'] == '月':
            for month in range(_delta + 1):
                # 未来 -> 過去
                # 2023/1/1 - 0か月, 1か月, 2か月.....
                accounting_month = end - relativedelta(months=month)
                # クローズ時期より以前は計上しない
                if accounting_month < close_date.replace(day=1):
                    break
                row['計上月'] = accounting_month.strftime('%Y-%m')
                row['計上ステータス'] = '受注予定'
                row['年度'] = calc_fy(
                    datetime.strptime(row['計上月'], '%Y-%m').date()
                )
                df = df.append(row.copy(), ignore_index=True)

        # 年契約
        elif row['契約形態'] == '年':
            for year in range(end.year, close_date.year, -1):
                # 計上終了月(ex: 2023-01-01) < 計上月(ex: 2023-03-01)
                #   - 計上終了月が 4月以降の場合、処理をスキップする
                accounting_month = date(year, close_date.month, 1)
                if end < accounting_month:
                    continue
                row['計上月'] = accounting_month.strftime('%Y-%m')
                row['計上ステータス'] = '受注予定'
                row['年度'] = calc_fy(
                    datetime.strptime(row['計上月'], '%Y-%m').date()
                )
                df = df.append(row.copy(), ignore_index=True)

    logger.info("======= 商談シート 売上計上処理 END =======")


    # 一部有料導入・全体有料導入の重複レコードを削除
    df = df[df['計上月'] != '']
    df_opportunity = df.loc[:1]
    for i in range(delta + 1):
        accounting_month = end - relativedelta(months=i)
        accounting_month = accounting_month.strftime('%Y-%m')
        try:
            # 計上月ごとに行分割
            tmp_df = df.groupby('計上月').get_group(accounting_month)
            # 一部有料導入・全体有料導入の両レコード間で、
            # 教育機関名Id が一致しているものは重複とする。
            #
            # keep='last' にすることで、一部有料導入の方を削除
            tmp_df = tmp_df[~tmp_df.duplicated(subset='教育機関名Id', keep='last')]
            # 行分割したものを再結合
            df_opportunity = df_opportunity.append(tmp_df)
        except:
            pass

    logger.info("======= 商談シート加工 END =======")


    ##############################
    # スプレッドシートへ書込み
    ##############################

    logger.info("======= 元データ書込み =======")
    workbook.worksheet('商談(Pandas)').clear()
    workbook.worksheet('契約(Pandas)').clear()
    set_with_dataframe(workbook.worksheet('商談(Pandas)'), df_opportunity, include_column_header=True)
    set_with_dataframe(workbook.worksheet('契約(Pandas)'), df_keiyaku, include_column_header=True)


    logger.info("======= 結合データ書込み (年度ごとにシートを分けて) =======")
    df_sum = pd.concat([df_keiyaku, df_opportunity], join='outer')
    df_sum = pd.pivot_table(
        df_sum,
        index=['年度','計上月','所有者'],
        columns='計上ステータス',
        values='MRR',
        aggfunc='sum',
        fill_value=0
    )
    df_sum = df_sum.fillna(0).sort_values(by='計上月').loc[:, ['確定','未確定','受注予定']]
    for year, _df in df_sum.groupby('年度'):
        # 合計行を追加
        _df.loc[('','','合計')] = _df.sum(numeric_only=True)

        # ビジネスサイド閲覧用のワークシートへ反映する
        SPREADSHEET_KEY = os.getenv("SP_KEY_2")
        workbook = gs.open_by_key(SPREADSHEET_KEY)

        try:
            workbook.worksheet(f'MRR-{year}').clear()
        except WorksheetNotFound as e:
            workbook.add_worksheet(title=f'MRR-{year}', rows=1000, cols=100)

        set_with_dataframe(
            workbook.worksheet(f'MRR-{year}'),
            _df,
            include_column_header=True,
            include_index=True
        )

    logger.info("======= END =======")

if __name__ == '__main__':
    handler()
