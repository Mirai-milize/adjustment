from datetime import datetime, timedelta
import calendar
import pandas as pd # pandas 라이브러리 임포트
import math # math.floor() 함수를 위해 임포트
from decimal import Decimal, getcontext # decimal 모듈 임포트
import sys # PyInstaller 번들링을 위해 임포트
import os # 파일 경로 조작을 위해 임포트
from tkinter import filedialog # 파일 대화상자를 위해 임포트
from tkinter import Tk # Tkinter 루트 윈도우를 위해 임포트

# Decimal 연산의 정밀도 설정
getcontext().prec = 10 # 필요에 따라 정밀도 조절

def resource_path(relative_path):
    """
    PyInstaller로 번들링된 애플리케이션에서 리소스의 절대 경로를 가져옵니다.
    """
    try:
        # PyInstaller가 생성한 임시 폴더 경로
        base_path = sys._MEIPASS
    except Exception:
        # 일반 파이썬 스크립트 실행 시 현재 디렉토리
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def calculate_total_payment(monthly_fee, payment_period, advance_payment):
  """
  총 결제금액을 계산합니다.
  (총 결제금액 = 월요금 * 결제기간 + 선수금)

  Args:
    monthly_fee: 월요금
    payment_period: 결제기간 (개월)
    advance_payment: 선수금

  Returns:
    총 결제금액
  """
  total_payment = (monthly_fee * payment_period) + advance_payment
  return total_payment

def get_last_day_of_month(date_obj):
    return date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])

def add_months_and_set_day(start_date, months_to_add, target_day):
    """
    Adds months to a start_date and sets the day to target_day,
    handling month-end overflows (e.g., if target_day is 31 and month has 30 days).
    """
    year = start_date.year
    month = start_date.month + months_to_add
    
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1

    _, last_day = calendar.monthrange(year, month)
    day = min(target_day, last_day)
    
    return datetime(year, month, day)

def calculate_prorated_amount(monthly_fee, start_date, end_date):
    """
    Calculates the prorated amount for a period within a month.
    Assumes start_date and end_date are within the same month.
    """
    if start_date.month != end_date.month or start_date.year != end_date.year:
        raise ValueError("Proration must be within the same month.")

    # 일일 요금 계산: (월요금 * 12) / 365
    daily_rate = (Decimal(str(monthly_fee)) * Decimal('12')) / Decimal('365')
    
    days_used = (end_date - start_date).days + 1 # +1 to include end_date
    
    return round(daily_rate * Decimal(str(days_used))) # Round to nearest integer for currency

def generate_prepayment_schedule(monthly_fee, payment_period_months, fixed_payment_day, delivery_date):
    """
    '선납' 방식의 자동차 렌트 요금 결제 스케줄을 생성합니다.

    Args:
      monthly_fee: 월요금
      payment_period_months: 총 결제 기간 (개월 수)
      fixed_payment_day: 매월 고정 결제일 (1-31)
      delivery_date: 차량 출고일 (datetime 객체)

    Returns:
      (payment_date, payment_amount) 튜플의 리스트
    """
    payment_schedule = []
    
    # Scenario 1: Delivery Date <= Fixed Payment Day in the same month
    # (e.g., Delivery Aug 10, Payment Day 15)
    if delivery_date.day <= fixed_payment_day:
        # 1. First payment: Day before delivery, for the current month's full fee
        first_payment_date = delivery_date - timedelta(days=1)
        payment_schedule.append((first_payment_date, monthly_fee))
        
        # 2. Regular payments for the remaining (payment_period_months - 1) months
        # These payments start from the fixed_payment_day of the *next* month after delivery.
        current_month_for_regular_payment = delivery_date.month + 1
        current_year_for_regular_payment = delivery_date.year
        if current_month_for_regular_payment > 12:
            current_month_for_regular_payment -= 12
            current_year_for_regular_payment += 1
            
        start_date_for_regular_payments = datetime(current_year_for_regular_payment, current_month_for_regular_payment, 1) # Use 1st to ensure add_months_and_set_day works correctly
        
        for i in range(payment_period_months - 1):
            payment_date = add_months_and_set_day(start_date_for_regular_payments, i, fixed_payment_day)
            payment_schedule.append((payment_date, monthly_fee))
            
        # The last month of the contract has no payment, as it was covered by the initial prepayment.
        
    # Scenario 2: Delivery Date > Fixed Payment Day in the same month
    # (e.g., Delivery Aug 21, Payment Day 15)
    else:
        # 1. First payment (1st installment): Day before delivery, for the NEXT month's full fee
        first_payment_date = delivery_date - timedelta(days=1)
        payment_schedule.append((first_payment_date, monthly_fee)) # This covers the next full month (e.g., Sept)

        # 2. Second payment (2nd installment): Prorated for the current month (delivery month)
        # This payment occurs on the fixed payment day of the *next* month.
        prorated_start_date = delivery_date
        prorated_end_date = get_last_day_of_month(delivery_date)
        prorated_amount = calculate_prorated_amount(monthly_fee, prorated_start_date, prorated_end_date)
        
        # The payment date for this prorated amount is the fixed payment day of the *next* month.
        second_payment_date = add_months_and_set_day(delivery_date, 1, fixed_payment_day)
        payment_schedule.append((second_payment_date, prorated_amount))
        
        # 3. Regular payments for the middle part of the contract
        # These payments cover `payment_period_months - 2` months.
        # They start from the month *after* the prorated payment.
        current_month_for_regular_payment = delivery_date.month + 2
        current_year_for_regular_payment = delivery_date.year
        if current_month_for_regular_payment > 12:
            current_month_for_regular_payment -= 12
            current_year_for_regular_payment += 1
            
        start_date_for_regular_payments = datetime(current_year_for_regular_payment, current_month_for_regular_payment, 1)
        
        for i in range(payment_period_months - 2):
            payment_date = add_months_and_set_day(start_date_for_regular_payments, i, fixed_payment_day)
            payment_schedule.append((payment_date, monthly_fee))
            
        # 4. Last payment: Prorated for the final month of the contract
        # The contract ends `payment_period_months` after the delivery date.
        # The last payment is for the period from the 1st of the last contract month
        # until the `delivery_date.day` of the last contract month.
        # The payment date is the `fixed_payment_day` of the last contract month.
        
        # Calculate the month of the last payment.
        # It's `delivery_date` + `payment_period_months` months.
        # The payment is made on the fixed_payment_day of this month.
        last_payment_month_date = add_months_and_set_day(delivery_date, payment_period_months, fixed_payment_day)
        
        # The prorated period for the last payment:
        # Start: 1st day of the last contract month.
        last_prorated_start_date = add_months_and_set_day(delivery_date, payment_period_months - 1, 1)
        # End: `delivery_date.day` of the last contract month.
        last_prorated_end_date = add_months_and_set_day(delivery_date, payment_period_months - 1, delivery_date.day)
        
        last_prorated_amount = calculate_prorated_amount(monthly_fee, last_prorated_start_date, last_prorated_end_date)
        
        payment_schedule.append((last_payment_month_date, last_prorated_amount))
        
    return payment_schedule

def generate_postpayment_schedule(monthly_fee, payment_period_months, fixed_payment_day, delivery_date):
    """
    '후납' 방식의 자동차 렌트 요금 결제 스케줄을 생성합니다.

    Args:
      monthly_fee: 월요금
      payment_period_months: 총 결제 기간 (개월 수)
      fixed_payment_day: 매월 고정 결제일 (1-31)
      delivery_date: 차량 출고일 (datetime 객체)

    Returns:
      (payment_date, payment_amount) 튜플의 리스트
    """
    payment_schedule = []

    # Scenario: Delivery Date < Fixed Payment Day in the same month
    # (e.g., Delivery Sep 6, Payment Day 10)
    if delivery_date.day < fixed_payment_day:
        # 1. First payment: Prorated for the delivery month (Sep 6 to Sep 30)
        # This payment occurs on the fixed payment day of the *next* month (Oct 10).
        prorated_start_date_first = delivery_date
        prorated_end_date_first = get_last_day_of_month(delivery_date)
        first_prorated_amount = calculate_prorated_amount(monthly_fee, prorated_start_date_first, prorated_end_date_first)

        first_payment_date = add_months_and_set_day(delivery_date, 1, fixed_payment_day)
        payment_schedule.append((first_payment_date, first_prorated_amount))

        # Determine the actual contract end date (vehicle return date)
        contract_end_date = add_months_and_set_day(delivery_date, payment_period_months, delivery_date.day)

        # Regular payments for the middle part of the contract
        # These payments cover `payment_period_months - 2` months.
        # They start from the month *after* the first prorated payment.
        # (e.g., Nov 10 for Oct, Dec 10 for Nov, etc.)
        if payment_period_months >= 2:
            start_date_for_regular_payments = add_months_and_set_day(delivery_date, 2, fixed_payment_day)

            for i in range(payment_period_months - 2):
                payment_date = add_months_and_set_day(start_date_for_regular_payments, i, fixed_payment_day)
                payment_schedule.append((payment_date, monthly_fee))

            # Last two payments: one full for the month before the final prorated, and one final prorated.
            # The month of the last full payment is the month before the contract_end_date's month.
            # The payment date for this is the fixed_payment_day of that month.
            last_full_payment_date = add_months_and_set_day(contract_end_date, -1, fixed_payment_day)
            payment_schedule.append((last_full_payment_date, monthly_fee))

            # Final prorated payment
            # Period: 1st of contract_end_date's month to contract_end_date
            final_prorated_start_date = contract_end_date.replace(day=1)
            final_prorated_amount = calculate_prorated_amount(monthly_fee, final_prorated_start_date, contract_end_date)
            payment_schedule.append((contract_end_date, final_prorated_amount))

    # Scenario: Delivery Date >= Fixed Payment Day in the same month
    # (e.g., Delivery Sep 15, Payment Day 10)
    else:
        # 1. First payment: Prorated for the delivery month
        # Payment date: fixed_payment_day of the *next* month
        prorated_start_date_first = delivery_date
        prorated_end_date_first = get_last_day_of_month(delivery_date)
        first_prorated_amount = calculate_prorated_amount(monthly_fee, prorated_start_date_first, prorated_end_date_first)

        first_payment_date = add_months_and_set_day(delivery_date, 1, fixed_payment_day)
        payment_schedule.append((first_payment_date, first_prorated_amount))

        # Determine the actual contract end date (vehicle return date)
        contract_end_date = add_months_and_set_day(delivery_date, payment_period_months, delivery_date.day)

        if payment_period_months >= 2:
            # Regular payments for the middle part of the contract
            # These payments cover `payment_period_months - 2` months.
            # They start from the month *after* the first prorated payment.
            # (e.g., Nov 10 for Oct, Dec 10 for Nov, etc.)
            start_date_for_regular_payments = add_months_and_set_day(delivery_date, 2, fixed_payment_day)

            for i in range(payment_period_months - 2):
                payment_date = add_months_and_set_day(start_date_for_regular_payments, i, fixed_payment_day)
                payment_schedule.append((payment_date, monthly_fee))

            # Last two payments: one full for the month before the final prorated, and one final prorated.
            # The month of the last full payment is the month before the contract_end_date's month.
            # The payment date for this is the fixed_payment_day of that month.
            last_full_payment_date = add_months_and_set_day(contract_end_date, -1, fixed_payment_day)
            payment_schedule.append((last_full_payment_date, monthly_fee))

            # Final prorated payment
            # Period: 1st of contract_end_date's month to contract_end_date
            final_prorated_start_date = contract_end_date.replace(day=1)
            final_prorated_amount = calculate_prorated_amount(monthly_fee, final_prorated_start_date, contract_end_date)
            payment_schedule.append((contract_end_date, final_prorated_amount))

    return payment_schedule

def read_collection_data_from_excel(file_path):
    """
    Excel 파일에서 수금 내역을 읽어옵니다.
    가정: '결제일', '결제금액' 컬럼이 존재합니다.
    '결제일' 컬럼은 날짜 및 시간 형식이어야 합니다.
    """
    try:
        df_collection = pd.read_excel(file_path)
        # 필요한 컬럼이 있는지 확인
        required_columns = ['결제일', '결제금액'] # '결제시간' 컬럼 제거
        if not all(col in df_collection.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df_collection.columns]
            raise KeyError(f"필요한 컬럼이 누락되었습니다: {', '.join(missing_cols)}")

        # '결제일' 컬럼을 datetime 형식으로 변환 (시간 정보 포함)
        df_collection['결제일'] = pd.to_datetime(df_collection['결제일'])
        # '결제 금액' 컬럼을 숫자로 변환 (오류 발생 시 NaN)
        df_collection['결제금액'] = pd.to_numeric(df_collection['결제금액'], errors='coerce')
        # 결제 금액이 NaN인 행 제거 (선택 사항, 필요에 따라)
        df_collection.dropna(subset=['결제금액'], inplace=True)

        return df_collection
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다: {file_path}")
        return None
    except KeyError as e:
        print(f"오류: Excel 파일에 필요한 컬럼이 없습니다. {e}")
        return None
    except Exception as e:
        print(f"수금 내역 Excel 파일을 읽는 중 오류 발생: {e}")
        return None

def calculate_overdue_for_installment(scheduled_date, base_monthly_fee, check_point_datetime):
    """
    단일 회차에 대한 연체 금액을 계산합니다.
    연체는 청구일(결제일) 이후 4일 뒤 12시 59분부터 시작됩니다.
    일일 연체 금액은 계약 시의 기본 월요금 * 0.0005479452 입니다.
    """
    # 연체 시작 기준 시점 (결제일 + 4일 + 12시간 59분)
    # 결제일은 datetime 객체이므로, 시간 정보가 없으면 00:00:00으로 간주됩니다.
    overdue_start_threshold = scheduled_date + timedelta(days=4, hours=12, minutes=59)

    # 현재 시간이 연체 시작 기준 시점보다 이전이면 연체 아님
    if check_point_datetime < overdue_start_threshold:
        return 0

    # 연체 일수 계산 (현재 시간 - 연체 시작 기준 시점)
    # timedelta의 total_seconds()를 사용하여 정확한 일수 계산
    # 연체 일수는 0.0005479452를 곱하는 기준이 되는 일수이므로, 소수점 이하를 올림하여 계산
    time_difference = check_point_datetime - overdue_start_threshold
    overdue_days = math.ceil(time_difference.total_seconds() / (24 * 3600))

    if overdue_days < 0: # 혹시 모를 음수 방지
        return 0

    # 총 연체 금액 (FLOOR 적용) - Decimal을 사용하여 정확한 계산 수행
    total_overdue = math.floor(Decimal(str(base_monthly_fee)) * Decimal('0.0005479452') * Decimal(str(overdue_days)))
    
    return total_overdue


if __name__ == "__main__":
    print("\n--- 자동차 렌트 요금 정산 스케줄 검증 및 Excel 내보내기 ---")

    try:
        monthly_fee = float(input("월요금을 입력하세요 (예: 500000): "))
        payment_period_months = int(input("총 결제 기간을 입력하세요 (개월, 예: 36): "))
        fixed_payment_day = int(input("매월 고정 결제일을 입력하세요 (1-31, 예: 25): "))
        delivery_date_str = input("차량 출고일을 입력하세요 (YYYY-MM-DD, 예: 2023-09-15): ")
        delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d')
        payment_type = input("지불 방식을 입력하세요 ('선납' 또는 '후납'): ")

        # 현재 날짜와 시간 가져오기
        current_datetime = datetime.now()
        print(f"현재 날짜 및 시간: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

        schedule = []
        if payment_type == '선납':
            schedule = generate_prepayment_schedule(monthly_fee, payment_period_months, fixed_payment_day, delivery_date)
        elif payment_type == '후납':
            schedule = generate_postpayment_schedule(monthly_fee, payment_period_months, fixed_payment_day, delivery_date)
        else:
            print("오류: 올바른 지불 방식을 입력해주세요 ('선납' 또는 '후납').")

        if schedule:
            print("\n--- 생성된 결제 스케줄 ---")
            # 스케줄을 DataFrame으로 변환
            df = pd.DataFrame(schedule, columns=['결제일', '월요금']) # '결제금액' -> '월요금'
            df.index.name = '회차'
            df.index = df.index + 1 # 회차를 1부터 시작하도록 조정
            
            # 납부월요금, 잔여월요금, 연체금액, 납부연체금액, 잔여연체금액, 최종납부일 컬럼 추가 및 초기화
            df['납부월요금'] = 0.0
            df['잔여월요금'] = df['월요금'] # 초기 잔여월요금은 월요금과 동일
            df['연체금액'] = 0.0 # 계산된 연체금액 (미납된 경우)
            df['납부연체금액'] = 0.0
            df['잔여연체금액'] = 0.0 # 초기 잔여연체금액은 0
            df['최종납부일'] = pd.NaT # 각 회차에 대한 최종 납부일 (datetime 객체), NaT로 초기화

            print(df.to_string()) # 콘솔 출력
            print("------------------------")

            # Excel 파일로 저장 여부 확인
            export_to_excel = input("스케줄을 Excel 파일로 저장하시겠습니까? (예/아니오): ").lower()
            if export_to_excel == '예':
                excel_filename = "상환스케쥴표.xlsx" # 파일 이름을 고정
                
                df.to_excel(excel_filename, index=True) 
                print(f"스케줄이 '{excel_filename}' 파일로 성공적으로 저장되었습니다.")
            else:
                print("Excel 파일 저장을 건너뛰었습니다.")

            # 수금 내역 Excel 파일 입력 여부 확인
            import_collection_data_choice = input("수금 내역 Excel 파일을 입력하시겠습니까? (예/아니오): ").lower()
            if import_collection_data_choice == '예':
                # Tkinter 루트 윈도우 생성 (숨김 처리)
                root = Tk()
                root.withdraw()
                
                collection_file_path = filedialog.askopenfilename(
                    title="수금 내역 Excel 파일 선택",
                    filetypes=[("Excel files", "*.xlsx *.xls")]
                )
                
                if collection_file_path:
                    df_collection = read_collection_data_from_excel(collection_file_path)
                    if df_collection is not None:
                        print("\n--- 읽어온 수금 내역 ---")
                        print(df_collection.to_string())
                        print("------------------------")
                        
                        # 수금 내역을 결제일 기준으로 정렬 (결제시간은 이미 결제일에 포함)
                        df_collection = df_collection.sort_values(by=['결제일']).reset_index(drop=True)

                        # 현재 청구된 회차 입력받기 (수금 적용 및 연체 계산 전에 필요)
                        try:
                            billed_installment_count = int(input("현재 몇 회차까지 청구되었는지 입력하세요: "))
                            if not (1 <= billed_installment_count <= len(df)):
                                print(f"오류: 청구 회차는 1에서 {len(df)} 사이의 값이어야 합니다.")
                                billed_installment_count = 0 # 유효하지 않은 경우 처리하지 않음
                        except ValueError:
                            print("오류: 청구 회차는 숫자로 입력해주세요.")
                            billed_installment_count = 0 # 유효하지 않은 경우 처리하지 않음

                        if billed_installment_count > 0:
                            print(f"현재 {billed_installment_count}회차까지 청구되었습니다.")

                            # 수금 내역을 결제 스케줄에 반영 (연체금액 우선, 그 다음 월요금)
                            collection_idx = 0
                            for inst_idx in range(len(df)): # 각 회차를 순회
                                if collection_idx >= len(df_collection): # 모든 수금 내역을 소진했으면 중단
                                    break

                                # 해당 회차에 수금액 반영
                                while collection_idx < len(df_collection) and \
                                      (df.loc[df.index[inst_idx], '잔여연체금액'] > 0 or df.loc[df.index[inst_idx], '잔여월요금'] > 0):
                                    
                                    collected_amount = df_collection.loc[collection_idx, '결제금액']
                                    collection_datetime_from_df = df_collection.loc[collection_idx, '결제일'] # 결제일 컬럼에서 직접 datetime 객체 가져옴

                                    if collected_amount <= 0: # 이미 소진된 수금액은 건너뛰기
                                        collection_idx += 1
                                        continue

                                    # 1. 잔여연체금액에 먼저 반영
                                    # 수금 시점의 연체금액을 계산하여 반영
                                    overdue_at_collection_time = calculate_overdue_for_installment(
                                        df.loc[df.index[inst_idx], '결제일'],
                                        monthly_fee, # 계약 시의 기본 월요금 사용
                                        collection_datetime_from_df # 수금 시점의 날짜와 시간으로 연체 계산
                                    )
                                    
                                    # 현재 회차의 총 연체금액을 업데이트 (수금 시점까지 발생한 연체)
                                    df.loc[df.index[inst_idx], '연체금액'] = overdue_at_collection_time
                                    
                                    # 잔여연체금액에 반영
                                    apply_to_overdue = min(collected_amount, df.loc[df.index[inst_idx], '잔여연체금액'])
                                    df.loc[df.index[inst_idx], '납부연체금액'] += apply_to_overdue
                                    df.loc[df.index[inst_idx], '잔여연체금액'] -= apply_to_overdue
                                    collected_amount -= apply_to_overdue
                                    
                                    # 2. 잔여월요금에 반영
                                    apply_to_principal = min(collected_amount, df.loc[df.index[inst_idx], '잔여월요금'])
                                    df.loc[df.index[inst_idx], '납부월요금'] += apply_to_principal
                                    df.loc[df.index[inst_idx], '잔여월요금'] -= apply_to_principal
                                    collected_amount -= apply_to_principal

                                    # 최종납부일 업데이트: 해당 회차에 금액이 반영될 때마다 업데이트
                                    if apply_to_overdue > 0 or apply_to_principal > 0:
                                        df.loc[df.index[inst_idx], '최종납부일'] = collection_datetime_from_df
                                    
                                    # df_collection의 해당 수금액 업데이트 (남은 금액이 있다면)
                                    df_collection.loc[collection_idx, '결제금액'] = collected_amount
                                    
                                    if collected_amount <= 0: # 해당 수금 건이 모두 소진되면 다음 수금 건으로
                                        collection_idx += 1
                                    else: # 수금 건이 남았지만 현재 회차 잔여금액/연체금액이 0이면 다음 회차로
                                        break
                            
                            # 최종 연체 금액 재계산 (수금 반영 후, current_datetime 기준)
                            for i in range(billed_installment_count):
                                # 해당 회차가 미납된 경우에만 연체 계산
                                if df.loc[df.index[i], '잔여월요금'] > 0 or df.loc[df.index[i], '잔여연체금액'] > 0:
                                    # 연체 계산 기준 날짜: 최종납부일이 있다면 그 날짜, 없으면 current_datetime
                                    # 하지만 최종 연체는 항상 current_datetime 기준으로 다시 계산
                                    final_overdue_amount = calculate_overdue_for_installment(
                                        df.loc[df.index[i], '결제일'], 
                                        monthly_fee, 
                                        current_datetime
                                    )
                                    # 최종 연체금액은 계산된 연체금액에서 납부된 연체금액을 제외한 값
                                    df.loc[df.index[i], '연체금액'] = final_overdue_amount
                                    df.loc[df.index[i], '잔여연체금액'] = max(0, final_overdue_amount - df.loc[df.index[i], '납부연체금액'])
                                else: # 완전히 납부된 회차는 연체금액 0
                                    df.loc[df.index[i], '연체금액'] = 0
                                    df.loc[df.index[i], '잔여연체금액'] = 0

                            print("\n--- 최종 결제 스케줄 (수금 및 연체 반영) ---")
                            # 모든 관련 컬럼 출력
                            print(df[['결제일', '월요금', '납부월요금', '잔여월요금', '연체금액', '납부연체금액', '잔여연체금액', '최종납부일']].to_string())
                            print("----------------------------------------")

                            # 업데이트된 스케줄을 Excel 파일로 저장 여부 확인
                            export_updated_to_excel = input("업데이트된 스케줄을 Excel 파일로 저장하시겠습니까? (예/아니오): ").lower()
                            if export_updated_to_excel == '예':
                                updated_excel_filename = "상환스케쥴표_업데이트.xlsx" # 업데이트된 파일 이름을 고정
                                df.to_excel(updated_excel_filename, index=True) 
                                print(f"업데이트된 스케줄이 '{updated_excel_filename}' 파일로 성공적으로 저장되었습니다.")
                            else:
                                print("업데이트된 Excel 파일 저장을 건너뛰었습니다.")

    except ValueError as e:
        print(f"입력 오류: {e}. 올바른 형식으로 입력해주세요.")
    except Exception as e:
        print(f"예상치 못한 오류가 발생했습니다: {e}")