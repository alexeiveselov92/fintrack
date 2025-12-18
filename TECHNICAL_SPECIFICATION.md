# Техническое задание: Personal Finance Tracker

## Версия 1.0 — MVP

---

## 1. Общее описание проекта

### 1.1 Назначение

Personal Finance Tracker — приложение для учёта и анализа личных финансов с фокусом на контроль расходов, планирование бюджета и достижение целей по сбережениям. Приложение позволяет пользователю анализировать свой денежный поток в целом, без привязки к конкретным счетам, с группировкой по категориям расходов.

### 1.2 Ключевые возможности MVP

Приложение реализует два взаимосвязанных сценария использования.

**Первый сценарий — работа без исторических данных** — позволяет пользователю на основе конфигурации доходов и планируемых расходов рассчитать бюджет на период и целевой объём сбережений. Этот режим полезен для первоначального планирования, когда пользователь ещё не накопил данных о своих тратах.

**Второй сценарий — работа с историческими данными** — обеспечивает анализ фактических транзакций, сравнение с планом, расчёт скользящих средних и выявление отклонений. Важно понимать, что второй сценарий является фундаментом для первого: чтобы реалистично спланировать траты по категориям, пользователю необходимо знать свои исторические расходы. Анализ истории позволяет выявить реальные паттерны трат и установить достижимые цели.

Ключевой особенностью является разделение расходов на **гибкие** (discretionary) и **фиксированные/регулярные** (fixed/recurring). Это разделение критически важно для планирования, так как позволяет пользователю видеть реально свободную сумму денег — ту часть бюджета, которой он может управлять, в отличие от фиксированных обязательств (аренда, подписки, страховки).

### 1.3 Технологический стек

Проект реализуется на Python версии 3.11 или выше. Для построения CLI интерфейса используется библиотека Typer. Валидация данных и описание моделей выполняется через Pydantic v2. Конфигурационные файлы хранятся в формате YAML и обрабатываются библиотекой PyYAML. Для персистентного хранения агрегированных данных и кэша применяется SQLite (с архитектурой, допускающей замену на другое хранилище). Генерация HTML-отчётов осуществляется с помощью шаблонизатора Jinja2.

### 1.4 Архитектурный подход

Архитектура приложения вдохновлена подходом dbt: пользователь работает с изолированными Workspace (аналог dbt project), каждый из которых содержит собственные конфигурации, данные транзакций и результаты расчётов. Взаимодействие происходит через CLI-команды, а все расчёты выполняются идемпотентно с использованием кэширования.

### 1.5 Требования к хранилищу данных

В MVP используется SQLite как простое и самодостаточное решение. Однако архитектура должна учитывать возможность перехода на другие хранилища в будущем:

- Более производительные решения (DuckDB, PostgreSQL)
- Облачные хранилища (для синхронизации между устройствами)
- Встраиваемые базы для мобильных приложений

Для этого слой работы с данными (storage layer) должен быть изолирован через абстракции (Repository pattern), чтобы замена хранилища не требовала изменений в бизнес-логике.

---

## 2. Глоссарий и терминология

### 2.1 Основные сущности

**Workspace** — изолированное рабочее пространство пользователя, содержащее все конфигурации, транзакции и результаты расчётов. Аналог "проекта" в dbt. У пользователя может быть несколько Workspace для разных целей (личные финансы, семейный бюджет, бизнес).

**Transaction** — единичная финансовая операция с указанием даты, суммы, валюты, категории и дополнительных флагов.

**BudgetPlan** — конфигурация финансовых параметров пользователя, действующая в определённый период времени. Содержит информацию о доходах, вычетах, целях по сбережениям, планируемых расходах по категориям и фиксированных расходах.

**Period** — временной интервал для агрегации и анализа данных. Настраивается в конфигурации Workspace и может быть: день, неделя, месяц (по умолчанию), квартал, год, или произвольное количество дней. Именование файлов планов адаптируется под выбранный интервал.

### 2.2 Финансовые термины

**Gross Income** — валовой доход до вычетов.

**Deductions** — обязательные вычеты из валового дохода (налоги, страховки), превращающие gross income в net income. Это вычеты, которые происходят до того, как деньги становятся доступны пользователю.

**Net Income** — чистый доход после всех вычетов, доступный для распределения.

**Fixed Expenses** — фиксированные/регулярные расходы из net income, которые пользователь обязан платить каждый период (аренда, коммунальные услуги, подписки, кредиты). Эти расходы вычитаются из net income для получения disposable income.

**Savings Target** — целевой объём сбережений за период, рассчитываемый как доля от выбранной базы (net income или disposable income, в зависимости от настройки пользователя).

**Disposable Income** — свободный доход после вычета фиксированных расходов и целевых сбережений. Это деньги, которыми пользователь реально может управлять.

**Spending Budget** — бюджет на гибкие расходы за период, равный net income минус fixed expenses минус savings target. Синоним Disposable Income в контексте бюджетирования.

**Category Budget** — планируемая сумма расходов по конкретной категории.

### 2.3 Флаги транзакций

**is_savings** — флаг, обозначающий транзакцию откладывания денег в сбережения. Такие транзакции учитываются отдельно и не влияют на spending budget. Пример: перевод на накопительный счёт.

**is_deduction** — флаг, обозначающий транзакцию обязательного вычета из валового дохода. Используется для автоматического расчёта net income на основе фактических данных. Пример: списание налога, оплата страховки, удержание из зарплаты.

**is_fixed** — флаг, обозначающий фиксированный/регулярный расход. Такие расходы вычитаются из net income при расчёте disposable income. Пример: аренда, подписки, коммунальные платежи, платежи по кредиту.

### 2.4 Логика расчёта свободных средств

Цепочка расчётов выглядит следующим образом:

```
Gross Income
  - Deductions (налоги, страховки — до получения денег)
= Net Income
  - Fixed Expenses (аренда, подписки, кредиты — обязательные траты)
  - Savings Target (целевые сбережения)
= Disposable Income / Spending Budget (свободные деньги для гибких трат)
```

**Выбор базы для расчёта сбережений (savings_base):**

Пользователь может выбрать, от какой суммы рассчитывать целевые сбережения:

1. **От Net Income (`savings_base: net_income`)** — сбережения рассчитываются до вычета фиксированных расходов. Это более амбициозный подход, который мотивирует оптимизировать фиксированные расходы. Формула: `Savings Target = Net Income × savings_rate`.

2. **От Disposable Income (`savings_base: disposable`)** — сбережения рассчитываются после вычета фиксированных расходов. Это реалистичный подход, когда фиксированные расходы невозможно или нецелесообразно уменьшать. Формула: `Disposable Base = Net Income - Fixed Expenses`, затем `Savings Target = Disposable Base × savings_rate`.

Пример разницы при Net Income = €3,800, Fixed Expenses = €1,065, savings_rate = 20%:
- От Net Income: €3,800 × 20% = €760 (остаётся €1,975 на гибкие траты)
- От Disposable: (€3,800 - €1,065) × 20% = €547 (остаётся €2,188 на гибкие траты)

Это разделение позволяет пользователю видеть реальную картину: сколько денег он может потратить на свое усмотрение, а сколько уже "заложено" в обязательства.

---

## 3. Модель данных

### 3.1 Transaction

Транзакция представляет собой единичную финансовую операцию со следующими атрибутами:

```python
class Transaction(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    date: date
    amount: Decimal  # положительное = доход, отрицательное = расход
    currency: str  # ISO 4217: EUR, RSD, USD
    category: str  # произвольная строка
    description: str | None = None
    is_savings: bool = False  # транзакция откладывания в сбережения
    is_deduction: bool = False  # вычет из gross income (налоги)
    is_fixed: bool = False  # фиксированный/регулярный расход
    source_file: str | None = None  # для отслеживания источника импорта
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Правила использования флагов:**

- `is_deduction` и `is_fixed` взаимоисключающие: deduction — это вычет ДО получения денег, fixed — это обязательный расход ИЗ полученных денег.
- `is_savings` может сочетаться с другими флагами, но обычно используется отдельно.
- Обычная транзакция (все флаги = false) считается гибким расходом/доходом.

Поле `amount` использует знак для определения направления: отрицательные значения означают расход, положительные — доход. Это обеспечивает простоту арифметических операций при агрегации.

Поле `category` принимает произвольные строки, поскольку ответственность за качество категоризации лежит на инструменте ввода транзакций (который не входит в MVP). При этом категории, используемые в BudgetPlan, служат ориентиром для пользователя.

Поле `source_file` сохраняет имя файла, из которого была импортирована транзакция, что необходимо для обеспечения идемпотентности импорта.

### 3.2 BudgetPlan

Конфигурация финансовых параметров пользователя:

```python
class DeductionItem(BaseModel):
    """Вычет из gross income (налоги, страховки до получения)"""
    name: str
    amount: Decimal
    
class FixedExpenseItem(BaseModel):
    """Фиксированный расход из net income"""
    name: str
    amount: Decimal
    category: str | None = None  # опциональная привязка к категории транзакций
    
class CategoryBudget(BaseModel):
    """Планируемый бюджет по категории"""
    category: str
    amount: Decimal
    is_fixed: bool = False  # если True, все транзакции этой категории считаются фиксированными

class SavingsBase(str, Enum):
    """База для расчёта целевых сбережений"""
    NET_INCOME = "net_income"  # от чистого дохода (до вычета фиксированных)
    DISPOSABLE = "disposable"  # от свободного дохода (после вычета фиксированных)

class BudgetPlan(BaseModel):
    id: str  # уникальный идентификатор плана
    valid_from: date
    valid_to: date | None = None  # None означает "действует бессрочно"
    
    gross_income: Decimal
    income_currency: str = "EUR"
    
    # Вычеты из gross income (налоги, страховки)
    deductions: list[DeductionItem] = []
    
    # Фиксированные расходы из net income (аренда, подписки)
    fixed_expenses: list[FixedExpenseItem] = []
    
    # Настройки сбережений
    savings_rate: Decimal = Decimal("0.20")  # целевая доля сбережений
    savings_base: SavingsBase = SavingsBase.NET_INCOME  # от чего считать
    
    # Планируемые бюджеты по категориям
    category_budgets: list[CategoryBudget] = []
    
    # Вычисляемые свойства
    @property
    def total_deductions(self) -> Decimal:
        return sum(d.amount for d in self.deductions)
    
    @property
    def net_income(self) -> Decimal:
        return self.gross_income - self.total_deductions
    
    @property
    def total_fixed_expenses(self) -> Decimal:
        return sum(f.amount for f in self.fixed_expenses)
    
    @property
    def savings_calculation_base(self) -> Decimal:
        """База для расчёта сбережений в зависимости от настройки"""
        if self.savings_base == SavingsBase.NET_INCOME:
            return self.net_income
        else:  # DISPOSABLE
            return self.net_income - self.total_fixed_expenses
    
    @property
    def savings_target(self) -> Decimal:
        return self.savings_calculation_base * self.savings_rate
    
    @property
    def disposable_income(self) -> Decimal:
        """Свободные деньги после фиксированных расходов и сбережений"""
        return self.net_income - self.total_fixed_expenses - self.savings_target
    
    @property
    def spending_budget(self) -> Decimal:
        """Синоним disposable_income для совместимости"""
        return self.disposable_income
    
    @property
    def fixed_categories(self) -> set[str]:
        """Категории, помеченные как фиксированные"""
        return {cb.category for cb in self.category_budgets if cb.is_fixed}
```

Поле `valid_to` со значением `None` означает, что план действует до появления следующего плана с более поздней датой `valid_from`. Система автоматически определяет применимый план для каждого периода.

### 3.3 ExchangeRate

Курс обмена валют:

```python
class ExchangeRate(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal  # множитель: amount_from * rate = amount_to
    valid_from: date
    valid_to: date | None = None
```

### 3.4 WorkspaceConfig

Конфигурация рабочего пространства:

```python
class IntervalType(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"  # для произвольного количества дней

class WorkspaceConfig(BaseModel):
    name: str
    description: str | None = None
    
    # Настройки периодизации
    interval: IntervalType = IntervalType.MONTH
    custom_interval_days: int | None = None  # только для interval=custom
    analysis_window: int = 3  # количество периодов для скользящего среднего
    
    # Валюты
    base_currency: str = "EUR"
    display_currencies: list[str] = []
    
    # Пути к файлам (относительно корня workspace)
    transactions_dir: str = "transactions"
    plans_dir: str = "plans"
    reports_dir: str = "reports"
    cache_db: str = ".cache/fintrack.db"
```

### 3.5 Агрегированные данные (для кэширования)

```python
class PeriodSummary(BaseModel):
    """Агрегированные данные за период для кэширования"""
    period_start: date
    period_end: date
    workspace_name: str
    
    # Фактические показатели
    total_income: Decimal
    total_expenses: Decimal  # все расходы (для общей картины)
    total_fixed_expenses: Decimal  # расходы с is_fixed=True
    total_flexible_expenses: Decimal  # расходы без is_fixed (гибкие)
    total_savings: Decimal  # сумма транзакций с is_savings=True
    total_deductions: Decimal  # сумма транзакций с is_deduction=True
    
    # Группировка по категориям
    expenses_by_category: dict[str, Decimal]
    fixed_expenses_by_category: dict[str, Decimal]
    flexible_expenses_by_category: dict[str, Decimal]
    
    # Метаданные
    transaction_count: int
    last_transaction_date: date | None
    calculated_at: datetime

class CategoryAnalysis(BaseModel):
    """Анализ категории за период"""
    period_start: date
    category: str
    is_fixed: bool  # категория помечена как фиксированная в плане
    
    actual_amount: Decimal
    planned_amount: Decimal | None  # из BudgetPlan
    historical_average: Decimal | None  # скользящее среднее
    
    # Отклонения (положительное = недорасход/экономия, отрицательное = перерасход)
    variance_vs_plan: Decimal | None
    variance_vs_history: Decimal | None
    
    # Доли
    share_of_spending_budget: Decimal  # доля от spending_budget (для гибких)
    share_of_total_expenses: Decimal  # доля от всех расходов
```

---

## 4. Структура файлов Workspace

### 4.1 Файловая структура

```
my_finances/                      # Корень workspace
├── workspace.yaml                # Конфигурация workspace
├── plans/                        # BudgetPlan конфигурации
│   ├── 2024-01.yaml             # для месячного интервала
│   ├── 2024-07.yaml
│   └── ...
├── rates.yaml                    # Курсы валют
├── transactions/                 # Исходные CSV файлы транзакций
│   ├── january_2024.csv
│   ├── february_2024.csv
│   └── ...
├── reports/                      # Сгенерированные HTML отчёты
│   └── ...
└── .cache/                       # Кэш и хранилище (автогенерируется)
    ├── fintrack.db              # SQLite база
    └── import_log.json          # Лог импортированных файлов
```

**Именование файлов планов в зависимости от интервала:**

| Интервал | Формат имени файла | Пример |
|----------|-------------------|--------|
| day | YYYY-MM-DD.yaml | 2024-01-15.yaml |
| week | YYYY-WNN.yaml | 2024-W03.yaml |
| month | YYYY-MM.yaml | 2024-01.yaml |
| quarter | YYYY-QN.yaml | 2024-Q1.yaml |
| year | YYYY.yaml | 2024.yaml |
| custom | YYYY-MM-DD.yaml | 2024-01-15.yaml (по дате начала) |

### 4.2 Формат workspace.yaml

```yaml
name: "personal_2024"
description: "Личные финансы 2024 года"

interval: "month"  # day, week, month, quarter, year, custom
# custom_interval_days: 14  # только если interval: custom

analysis_window: 3  # количество периодов для скользящего среднего

base_currency: "EUR"
display_currencies:
  - "RSD"
  - "USD"

transactions_dir: "transactions"
plans_dir: "plans"
reports_dir: "reports"
cache_db: ".cache/fintrack.db"
```

### 4.3 Формат BudgetPlan (plans/2024-01.yaml)

```yaml
id: "plan_2024_01"
valid_from: "2024-01-01"
valid_to: null  # действует до следующего плана

gross_income: 5000.00
income_currency: "EUR"

# Вычеты из gross income (до получения денег)
deductions:
  - name: "income_tax"
    amount: 1000.00
  - name: "social_security"
    amount: 200.00

# Фиксированные расходы из net income (обязательные платежи)
fixed_expenses:
  - name: "rent"
    amount: 800.00
    category: "housing"  # привязка к категории транзакций
  - name: "utilities"
    amount: 150.00
    category: "utilities"
  - name: "internet"
    amount: 30.00
    category: "subscriptions"
  - name: "phone"
    amount: 20.00
    category: "subscriptions"
  - name: "gym"
    amount: 40.00
    category: "health"
  - name: "streaming_services"
    amount: 25.00
    category: "subscriptions"

# Настройки сбережений
savings_rate: 0.20  # 20% от выбранной базы
savings_base: "net_income"  # "net_income" или "disposable"
# net_income — от чистого дохода (мотивирует оптимизировать фиксированные расходы)
# disposable — от свободного дохода (реалистичный подход при неизменяемых фиксах)

# Планируемые бюджеты по категориям
category_budgets:
  # Фиксированные категории (is_fixed: true)
  - category: "housing"
    amount: 800.00
    is_fixed: true
  - category: "utilities"
    amount: 150.00
    is_fixed: true
  - category: "subscriptions"
    amount: 75.00
    is_fixed: true
    
  # Гибкие категории
  - category: "food"
    amount: 400.00
  - category: "transport"
    amount: 150.00
  - category: "entertainment"
    amount: 150.00
  - category: "clothing"
    amount: 100.00
  - category: "health"
    amount: 50.00  # сверх фикса на gym
```

**Расчёт на основе этого плана (savings_base: net_income):**
```
Gross Income:           €5,000.00
- Deductions:           €1,200.00 (tax + social)
= Net Income:           €3,800.00
- Fixed Expenses:       €1,065.00 (rent + utilities + subscriptions + gym)
- Savings Target (20% от Net Income): €760.00
= Disposable Income:    €1,975.00 (свободные деньги)
```

**Альтернативный расчёт (savings_base: disposable):**
```
Gross Income:           €5,000.00
- Deductions:           €1,200.00 (tax + social)
= Net Income:           €3,800.00
- Fixed Expenses:       €1,065.00 (rent + utilities + subscriptions + gym)
= Pre-Savings Disposable: €2,735.00
- Savings Target (20% от Disposable): €547.00
= Disposable Income:    €2,188.00 (свободные деньги)
```

### 4.4 Формат rates.yaml

```yaml
rates:
  - from_currency: "EUR"
    to_currency: "RSD"
    rate: 117.5
    valid_from: "2024-01-01"
    valid_to: "2024-06-30"
    
  - from_currency: "EUR"
    to_currency: "RSD"
    rate: 117.2
    valid_from: "2024-07-01"
    valid_to: null
    
  - from_currency: "USD"
    to_currency: "EUR"
    rate: 0.92
    valid_from: "2024-01-01"
    valid_to: null
```

### 4.5 Формат CSV транзакций

```csv
date,amount,currency,category,description,is_savings,is_deduction,is_fixed
2024-01-01,-800.00,EUR,housing,Monthly rent,,, true
2024-01-02,-45.50,EUR,food,Grocery store,,,
2024-01-03,-30.00,EUR,subscriptions,Internet,,, true
2024-01-05,-12.00,EUR,transport,Bus ticket,,,
2024-01-10,5000.00,EUR,salary,January salary,,,
2024-01-10,-1000.00,EUR,tax,Income tax,, true,
2024-01-15,-500.00,EUR,savings,Monthly savings, true,,
2024-01-20,-85.00,EUR,entertainment,Concert tickets,,,
```

Пустые значения в булевых полях интерпретируются как `false`.

---

## 5. Система кэширования и идемпотентность

### 5.1 Принципы

Приложение обеспечивает идемпотентность операций: повторный запуск команды с теми же входными данными не приводит к дублированию или искажению результатов. Это достигается через систему кэширования.

### 5.2 Абстракция хранилища (Repository Pattern)

Для обеспечения возможности замены хранилища, весь доступ к данным осуществляется через абстрактные интерфейсы:

```python
from abc import ABC, abstractmethod

class TransactionRepository(ABC):
    @abstractmethod
    def save(self, transaction: Transaction) -> None: ...
    
    @abstractmethod
    def save_batch(self, transactions: list[Transaction]) -> int: ...
    
    @abstractmethod
    def get_by_period(self, start: date, end: date) -> list[Transaction]: ...
    
    @abstractmethod
    def get_by_category(self, category: str, start: date | None = None, end: date | None = None) -> list[Transaction]: ...
    
    @abstractmethod
    def exists(self, date: date, amount: Decimal, currency: str, category: str, description: str | None) -> bool: ...

class CacheRepository(ABC):
    @abstractmethod
    def get_period_summary(self, period_start: date, workspace: str) -> PeriodSummary | None: ...
    
    @abstractmethod
    def save_period_summary(self, summary: PeriodSummary) -> None: ...
    
    @abstractmethod
    def invalidate_period(self, period_start: date, workspace: str) -> None: ...
    
    @abstractmethod
    def invalidate_all(self, workspace: str) -> None: ...

class ImportLogRepository(ABC):
    @abstractmethod
    def is_imported(self, file_hash: str) -> bool: ...
    
    @abstractmethod
    def log_import(self, file_path: str, file_hash: str, records_count: int) -> None: ...
```

### 5.3 SQLite реализация (MVP)

```sql
-- Импортированные транзакции
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    amount DECIMAL NOT NULL,
    currency TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    is_savings BOOLEAN DEFAULT FALSE,
    is_deduction BOOLEAN DEFAULT FALSE,
    is_fixed BOOLEAN DEFAULT FALSE,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, amount, currency, category, description)
);

CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category);

-- Лог импорта файлов
CREATE TABLE import_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,  -- SHA256 хэш содержимого
    records_imported INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_hash)
);

-- Кэш агрегированных данных по периодам
CREATE TABLE period_summaries (
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    workspace_name TEXT NOT NULL,
    total_income DECIMAL,
    total_expenses DECIMAL,
    total_fixed_expenses DECIMAL,
    total_flexible_expenses DECIMAL,
    total_savings DECIMAL,
    total_deductions DECIMAL,
    expenses_by_category JSON,
    fixed_expenses_by_category JSON,
    flexible_expenses_by_category JSON,
    transaction_count INTEGER,
    last_transaction_date DATE,
    calculated_at TIMESTAMP,
    PRIMARY KEY (period_start, workspace_name)
);

-- Кэш анализа по категориям
CREATE TABLE category_analysis (
    period_start DATE NOT NULL,
    category TEXT NOT NULL,
    workspace_name TEXT NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    actual_amount DECIMAL,
    planned_amount DECIMAL,
    historical_average DECIMAL,
    variance_vs_plan DECIMAL,
    variance_vs_history DECIMAL,
    share_of_spending_budget DECIMAL,
    share_of_total_expenses DECIMAL,
    calculated_at TIMESTAMP,
    PRIMARY KEY (period_start, category, workspace_name)
);
```

### 5.4 Логика идемпотентного импорта

При импорте CSV файла система выполняет следующие шаги:

1. Вычисляется SHA256 хэш содержимого файла.
2. Проверяется наличие этого хэша в таблице `import_log`.
3. Если хэш найден, файл пропускается с сообщением "Already imported".
4. Если хэш не найден, выполняется импорт транзакций с проверкой дубликатов по уникальному ключу `(date, amount, currency, category, description)`.
5. После успешного импорта хэш записывается в `import_log`.

### 5.5 Инвалидация кэша

Кэш агрегированных данных (`period_summaries`, `category_analysis`) инвалидируется при:
- Импорте новых транзакций, затрагивающих соответствующий период
- Изменении BudgetPlan для периода (определяется по дате модификации файла)

Инвалидация выполняется удалением записей из кэш-таблиц; при следующем запросе данные пересчитываются.

---

## 6. Алгоритмы расчётов

### 6.1 Сценарий без исторических данных

**Входные данные:** BudgetPlan для запрашиваемого периода.

**Алгоритм:**

1. Найти применимый BudgetPlan по дате периода (`valid_from <= period_start`, `valid_to` is null или `valid_to >= period_start`).
2. Рассчитать `net_income = gross_income - sum(deductions)`.
3. Рассчитать `total_fixed = sum(fixed_expenses)`.
4. Определить базу для сбережений в зависимости от `savings_base`:
   - Если `savings_base = net_income`: `savings_calculation_base = net_income`
   - Если `savings_base = disposable`: `savings_calculation_base = net_income - total_fixed`
5. Рассчитать `savings_target = savings_calculation_base × savings_rate`.
6. Рассчитать `disposable_income = net_income - total_fixed - savings_target`.
7. Разделить `category_budgets` на фиксированные и гибкие.
8. Для гибких категорий рассчитать долю от `disposable_income`.

**Выходные данные:**

```python
class BudgetProjection(BaseModel):
    period: str  # "2024-01"
    plan_id: str
    
    gross_income: Decimal
    total_deductions: Decimal
    deductions_breakdown: list[DeductionItem]
    net_income: Decimal
    
    total_fixed_expenses: Decimal
    fixed_expenses_breakdown: list[FixedExpenseItem]
    
    # Сбережения с указанием базы расчёта
    savings_base: SavingsBase
    savings_calculation_base: Decimal  # от чего считали
    savings_rate: Decimal
    savings_target: Decimal
    
    disposable_income: Decimal  # свободные деньги
    
    # Разбивка по категориям
    fixed_category_budgets: list[CategoryBudgetProjection]
    flexible_category_budgets: list[CategoryBudgetProjection]
    
    total_allocated_flexible: Decimal
    unallocated_flexible: Decimal  # disposable_income - total_allocated_flexible

class CategoryBudgetProjection(BaseModel):
    category: str
    amount: Decimal
    is_fixed: bool
    share_of_budget: Decimal  # доля от disposable_income (для гибких)
```

### 6.2 Сценарий с историческими данными

#### 6.2.1 Агрегация транзакций за период

**Входные данные:** список транзакций, границы периода, BudgetPlan (для определения фиксированных категорий).

**Алгоритм:**

1. Отфильтровать транзакции по дате (`period_start <= date < period_end`).
2. Конвертировать все суммы в `base_currency` по актуальному курсу.
3. Определить фиксированные категории из BudgetPlan (`is_fixed: true`).
4. Разделить транзакции на группы:
   - Доходы: `amount > 0`, не `is_deduction`
   - Deductions: `is_deduction = true`
   - Сбережения: `is_savings = true`
   - Фиксированные расходы: `amount < 0`, не `is_savings`, не `is_deduction`, и (`is_fixed = true` ИЛИ `category` в фиксированных категориях)
   - Гибкие расходы: все остальные расходы
5. Для каждой группы расходов сгруппировать по `category` и посчитать суммы.
6. Сохранить результат в `period_summaries`.

#### 6.2.2 Расчёт скользящего среднего

**Входные данные:** текущий период, `analysis_window` из конфига.

**Алгоритм:**

1. Определить N предыдущих периодов (где N = `analysis_window`).
2. Для каждой категории собрать суммы расходов за эти периоды.
3. Рассчитать среднее: `historical_average = sum(amounts) / count(periods_with_data)`.
4. Периоды без данных не учитываются в знаменателе.
5. Отдельно рассчитать средние для фиксированных и гибких категорий.

#### 6.2.3 Анализ отклонений

**Входные данные:** PeriodSummary, применимый BudgetPlan, скользящие средние.

**Алгоритм для каждой категории:**

1. `actual_amount` = фактическая сумма расходов по категории (из PeriodSummary).
2. `planned_amount` = сумма из `category_budgets` в BudgetPlan (null если категория не запланирована).
3. `historical_average` = скользящее среднее (null если нет исторических данных).
4. `variance_vs_plan = planned_amount - actual_amount`:
   - Положительное значение = экономия/недорасход
   - Отрицательное значение = перерасход
   - Если `planned_amount` is null, результат null.
5. `variance_vs_history = historical_average - actual_amount`.
6. Для гибких категорий: `share_of_spending_budget = actual_amount / disposable_income`.
7. Для всех категорий: `share_of_total_expenses = actual_amount / total_expenses`.

#### 6.2.4 Общий анализ периода

**Расчёты:**

1. `actual_spending = sum` всех расходов.
2. `actual_fixed_spending = sum` фиксированных расходов.
3. `actual_flexible_spending = sum` гибких расходов.
4. `actual_savings = sum` транзакций с `is_savings = true`.
5. `actual_deductions = sum` транзакций с `is_deduction = true`.
6. `calculated_net_income = total_income - actual_deductions`.
7. `savings_achievement = actual_savings / savings_target × 100%`.
8. `fixed_variance = planned_fixed - actual_fixed` (показывает стабильность фиксированных расходов).
9. `flexible_variance = disposable_income - actual_flexible_spending`:
   - Положительное = остались в бюджете свободных трат
   - Отрицательное = перерасход свободного бюджета

---

## 7. CLI интерфейс

### 7.1 Общая структура команд

```bash
fintrack <command> [options]
```

Все команды выполняются в контексте текущего workspace (определяется по наличию `workspace.yaml` в текущей директории или указывается явно через `--workspace`).

### 7.2 Команды

#### fintrack init

Создание нового workspace.

```bash
fintrack init <name> [--interval <type>] [--currency <code>]
```

Создаёт директорию с именем `name` и базовую структуру файлов:
- `workspace.yaml` с настройками по умолчанию
- Пустые директории `plans`, `transactions`, `reports`
- Пример BudgetPlan (`plans/example.yaml`)

#### fintrack validate

Валидация конфигурации workspace.

```bash
fintrack validate [--fix]
```

Проверяет:
- Корректность `workspace.yaml`
- Валидность всех BudgetPlan файлов
- Формат `rates.yaml`
- Отсутствие пересечений периодов в BudgetPlan
- Корректность ссылок на категории

Флаг `--fix` пытается автоматически исправить незначительные ошибки.

#### fintrack import

Импорт транзакций из CSV.

```bash
fintrack import <file_or_directory> [--force]
```

Импортирует транзакции из указанного файла или всех CSV файлов в директории. Использует идемпотентный импорт (пропускает уже импортированные файлы). Флаг `--force` игнорирует кэш и импортирует заново.

Вывод:
```
Importing transactions...
  january_2024.csv: 45 records imported
  february_2024.csv: skipped (already imported)
  march_2024.csv: 52 records imported
Total: 97 new records imported
```

#### fintrack budget

Расчёт бюджета (без исторических данных).

```bash
fintrack budget [--period <YYYY-MM>]
```

Если период не указан, используется текущий период согласно настройке `interval`. Выводит проекцию бюджета на основе BudgetPlan с разделением на фиксированные и гибкие расходы.

Вывод:
```
Budget Projection for 2024-01
═══════════════════════════════════════════════════════

Income
  Gross income:              €5,000.00
  Deductions:
    - income_tax:            €1,000.00
    - social_security:         €200.00
  Total deductions:          €1,200.00
  ─────────────────────────────────────
  Net income:                €3,800.00

Fixed Expenses (from net income)
    - rent:                    €800.00  [housing]
    - utilities:               €150.00  [utilities]
    - internet:                 €30.00  [subscriptions]
    - phone:                    €20.00  [subscriptions]
    - gym:                      €40.00  [health]
    - streaming:                €25.00  [subscriptions]
  Total fixed:               €1,065.00

Savings (based on: net_income)
  Calculation base:          €3,800.00
  Target rate:               20%
  Target amount:               €760.00

═══════════════════════════════════════════════════════
Disposable Income:           €1,975.00
═══════════════════════════════════════════════════════

Flexible Category Budgets (from disposable)
  food:                        €400.00  (20.3%)
  transport:                   €150.00  (7.6%)
  entertainment:               €150.00  (7.6%)
  clothing:                    €100.00  (5.1%)
  health:                       €50.00  (2.5%)
  ─────────────────────────────────────
  Total allocated:             €850.00  (43.0%)
  Unallocated:               €1,125.00  (57.0%)
```

#### fintrack status

Статус текущего периода.

```bash
fintrack status [--period <YYYY-MM>]
```

Показывает краткую сводку: прогресс по бюджету, сбережениям, предупреждения о перерасходе.

Вывод:
```
Status for 2024-01 (15 days remaining)
═══════════════════════════════════════════════════════

Fixed Expenses
  Budget:                    €1,065.00
  Spent:                     €1,065.00  (100.0%) ✓

Flexible Spending
  Budget (disposable):       €1,975.00
  Spent so far:                €650.00  (32.9%)
  Remaining:                 €1,325.00

Savings Progress
  Target:                      €760.00
  Saved so far:                €400.00  (52.6%)

⚠ Warnings
  - Category 'entertainment' at 85% of monthly budget (15 days left)
  - On track to exceed flexible budget by €200 at current pace
```

#### fintrack analyze

Полный анализ с историческими данными.

```bash
fintrack analyze [--from <YYYY-MM>] [--to <YYYY-MM>] [--category <name>]
```

По умолчанию анализирует последние N периодов (`analysis_window` из конфига).

Вывод:
```
Analysis for 2024-03
═══════════════════════════════════════════════════════

Disposable Income: €1,975.00

Fixed Categories (variance from plan)
                     Actual    Planned   Variance
  housing            €800.00   €800.00      €0.00  ✓
  utilities          €155.00   €150.00     -€5.00
  subscriptions       €75.00    €75.00      €0.00  ✓
  ──────────────────────────────────────────────────
  Fixed total      €1,030.00 €1,025.00     -€5.00

Flexible Categories (vs plan and 3-month average)
                     Actual    Planned   Avg(3mo)  vs Plan   vs Avg
  food               €420.00   €400.00   €385.00   -€20.00   -€35.00
  transport          €130.00   €150.00   €145.00   +€20.00   +€15.00
  entertainment      €250.00   €150.00   €180.00  -€100.00   -€70.00
  clothing            €80.00   €100.00    €95.00   +€20.00   +€15.00
  health              €45.00    €50.00    €48.00    +€5.00    +€3.00
  other              €180.00       -     €165.00       -     -€15.00
  ──────────────────────────────────────────────────────────────────
  Flexible total   €1,105.00   €850.00   €918.00  -€255.00  -€187.00

Savings
  Target:              €760.00
  Actual:              €550.00
  Achievement:         72.4%

Summary
  Fixed budget:       -€5.00 over plan
  Flexible budget:   +€870.00 remaining (of €1,975.00 disposable)
  Savings shortfall: -€210.00 from target
```

#### fintrack report

Генерация HTML отчёта.

```bash
fintrack report [--period <YYYY-MM>] [--output <filename>]
```

Генерирует подробный HTML отчёт с графиками и таблицами.

#### fintrack list

Вспомогательные команды для просмотра данных.

```bash
fintrack list transactions [--period <YYYY-MM>] [--category <name>] [--fixed-only | --flexible-only]
fintrack list plans
fintrack list categories [--fixed | --flexible]
```

#### fintrack cache

Управление кэшем.

```bash
fintrack cache clear [--all | --period <YYYY-MM>]
fintrack cache status
```

---

## 8. Структура кодовой базы

```
fintrack/
├── fintrack/
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py              # Typer app, группировка команд
│   │   ├── init.py              # fintrack init
│   │   ├── validate.py          # fintrack validate
│   │   ├── import_cmd.py        # fintrack import
│   │   ├── budget.py            # fintrack budget
│   │   ├── status.py            # fintrack status
│   │   ├── analyze.py           # fintrack analyze
│   │   ├── report.py            # fintrack report
│   │   └── utils.py             # CLI утилиты, форматирование вывода
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py            # Pydantic модели
│   │   ├── workspace.py         # Загрузка и управление Workspace
│   │   ├── plan.py              # Работа с BudgetPlan
│   │   ├── exceptions.py        # Кастомные исключения
│   │   └── constants.py         # Константы, дефолты
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── calculator.py        # Расчёты бюджета
│   │   ├── aggregator.py        # Агрегация транзакций
│   │   ├── analyzer.py          # Анализ отклонений
│   │   ├── currency.py          # Конвертация валют
│   │   └── periods.py           # Работа с периодами разных типов
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py              # Абстрактные репозитории (interfaces)
│   │   ├── sqlite/
│   │   │   ├── __init__.py
│   │   │   ├── database.py      # SQLite подключение и миграции
│   │   │   ├── transactions.py  # SQLite реализация TransactionRepository
│   │   │   ├── cache.py         # SQLite реализация CacheRepository
│   │   │   └── import_log.py    # SQLite реализация ImportLogRepository
│   │   └── factory.py           # Фабрика для создания репозиториев
│   │
│   ├── io/
│   │   ├── __init__.py
│   │   ├── csv_reader.py        # Чтение CSV
│   │   ├── yaml_reader.py       # Чтение YAML конфигов
│   │   └── yaml_writer.py       # Запись YAML
│   │
│   └── reports/
│       ├── __init__.py
│       ├── generator.py         # Генерация HTML
│       └── templates/
│           ├── base.html
│           ├── report.html
│           ├── budget.html
│           └── styles.css
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_models.py
│   ├── test_calculator.py
│   ├── test_aggregator.py
│   ├── test_analyzer.py
│   ├── test_import.py
│   ├── test_periods.py
│   └── test_cli.py
│
├── examples/
│   └── demo_workspace/          # Пример workspace с данными
│
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

---

## 9. HTML отчёт

### 9.1 Структура отчёта

HTML отчёт содержит следующие секции:

**Заголовок и метаданные:** название workspace, период отчёта, дата генерации.

**Сводка периода:** ключевые показатели в виде карточек:
- Net income
- Fixed expenses (план vs факт)
- Disposable income
- Фактические расходы (гибкие)
- Сбережения (план vs факт)
- Процент достижения целей

**Прогресс по фиксированным расходам:** таблица с колонками: категория, план, факт, отклонение. Визуальные индикаторы стабильности.

**Прогресс по гибким категориям:** таблица с колонками: категория, план, факт, скользящее среднее, отклонение от плана, отклонение от среднего. Визуальные индикаторы (progress bars).

**Анализ свободных средств:** сколько осталось от disposable income, прогноз на конец периода.

**Тренды:** если данных достаточно, графики расходов по категориям за несколько периодов. Отдельные графики для фиксированных и гибких расходов. Реализация через inline SVG или Chart.js (встроенный в HTML).

**Предупреждения и рекомендации:** категории с перерасходом, нестабильность фиксированных расходов, риск не достичь цели по сбережениям, тренды ухудшения.

### 9.2 Стилизация

Отчёт должен быть:
- Самодостаточным (все стили inline или в теге `<style>`)
- Адаптивным для просмотра на мобильных устройствах
- Пригодным для печати

---

## 10. Обработка ошибок

### 10.1 Типы исключений

```python
class FintrackError(Exception):
    """Базовое исключение приложения"""
    pass

class WorkspaceNotFoundError(FintrackError):
    """Workspace не найден в текущей директории"""
    pass

class InvalidConfigError(FintrackError):
    """Ошибка в конфигурационном файле"""
    pass

class NoPlanFoundError(FintrackError):
    """Не найден BudgetPlan для указанного периода"""
    pass

class CurrencyConversionError(FintrackError):
    """Невозможно конвертировать валюту (нет курса)"""
    pass

class ImportError(FintrackError):
    """Ошибка при импорте транзакций"""
    pass

class StorageError(FintrackError):
    """Ошибка при работе с хранилищем данных"""
    pass
```

### 10.2 Поведение CLI

- Все команды выводят понятные сообщения об ошибках с указанием пути к проблемному файлу и номера строки (где применимо).
- Код возврата: 0 при успехе, 1 при ошибке.
- Флаг `--verbose` включает подробный вывод и stack trace.

---

## 11. Тестирование

### 11.1 Стратегия

**Unit-тесты** покрывают:
- Модели (валидация Pydantic)
- Расчёты (calculator, analyzer)
- Агрегацию
- Работу с периодами разных типов
- Разделение на фиксированные/гибкие расходы

**Интеграционные тесты** проверяют:
- Полный цикл: создание workspace, импорт, анализ, генерацию отчёта
- Идемпотентность импорта
- Корректность кэширования и инвалидации

**Fixtures** включают:
- Тестовый workspace с набором транзакций
- BudgetPlan для нескольких периодов
- Различные сценарии (только фиксированные, только гибкие, смешанные)

### 11.2 Тестовые данные

Проект включает `examples/demo_workspace` с реалистичными тестовыми данными за 6 месяцев для демонстрации и ручного тестирования.

---

## 12. Фазы реализации

### Фаза 1: Фундамент (приоритет: высокий)

**Задачи:**
- Структура проекта и `pyproject.toml`
- Pydantic модели (Transaction, BudgetPlan, WorkspaceConfig, ExchangeRate)
- Чтение YAML конфигов
- Базовый CLI каркас (init, validate)
- Абстракции репозиториев (interfaces)
- SQLite схема и реализация репозиториев

**Критерии готовности:**
- Команда `fintrack init` создаёт валидный workspace
- Команда `fintrack validate` проверяет конфиги
- Модели корректно обрабатывают все три флага (is_savings, is_deduction, is_fixed)

### Фаза 2: Импорт и хранение (приоритет: высокий)

**Задачи:**
- Чтение CSV транзакций с поддержкой всех флагов
- Идемпотентный импорт с хэшированием
- Сохранение через репозитории
- Команда `fintrack import`

**Критерии готовности:**
- Повторный импорт того же файла не создаёт дубликатов
- Флаги корректно парсятся из CSV

### Фаза 3: Расчёты бюджета (приоритет: высокий)

**Задачи:**
- Калькулятор бюджета (без истории) с разделением fixed/flexible
- Работа с периодами разных типов (day, week, month, etc.)
- Команда `fintrack budget`
- Базовый `fintrack status`

**Критерии готовности:**
- `fintrack budget` выводит корректную проекцию с disposable income
- Поддержка разных типов интервалов

### Фаза 4: Аналитика (приоритет: средний)

**Задачи:**
- Агрегация транзакций по периодам с разделением fixed/flexible
- Кэширование агрегатов
- Скользящее среднее
- Анализ отклонений
- Конвертация валют
- Команда `fintrack analyze`

**Критерии готовности:**
- `fintrack analyze` показывает сравнение факт/план/история
- Отдельный анализ для фиксированных и гибких категорий

### Фаза 5: Отчёты (приоритет: средний)

**Задачи:**
- Jinja2 шаблоны
- Генерация HTML с разделами fixed/flexible
- Базовая визуализация
- Команда `fintrack report`

**Критерии готовности:**
- Генерируется самодостаточный HTML файл с отчётом
- Чётко выделены фиксированные и свободные средства

### Фаза 6: Полировка (приоритет: низкий)

**Задачи:**
- Улучшение UX CLI
- Подробные сообщения об ошибках
- Документация
- Примеры

---

## 13. Открытые вопросы для будущих версий

Следующие возможности не входят в MVP, но должны учитываться в архитектуре:

**Интерактивный ввод транзакций:** команда `fintrack add` с валидацией и автодополнением категорий.

**Импорт банковских выписок:** парсинг выписок различных банков с маппингом на категории и автоматическим определением флагов.

**Веб-интерфейс:** FastAPI backend + фронтенд для визуализации и ввода данных.

**Мобильное приложение:** архитектура должна позволять использовать тот же engine из мобильного приложения (через API или встроенный Python).

**Мультипользовательность:** несколько пользователей в одном workspace (семейный бюджет).

**Множественные счета:** добавление поля `account` в Transaction для отслеживания балансов по счетам.

**Альтернативные хранилища:** DuckDB для аналитики, PostgreSQL для серверного развёртывания, облачные решения для синхронизации.

**Прогнозирование:** ML-модели для предсказания расходов и рекомендаций по бюджету.

---

## 14. Принятые решения и обоснования

**Pydantic вместо dataclasses:** встроенная валидация, сериализация в JSON/dict, лучшая интеграция с YAML.

**SQLite для MVP с абстракцией:** простота развёртывания (один файл), но Repository pattern позволяет заменить на любое хранилище без изменения бизнес-логики.

**YAML для конфигов:** человекочитаемый формат, поддержка комментариев, стандарт для конфигурационных файлов.

**Знак суммы для определения направления:** упрощает агрегацию (просто sum), соответствует бухгалтерской практике.

**Произвольные категории:** гибкость для пользователя, категоризация — ответственность инструмента ввода.

**Три флага (is_savings, is_deduction, is_fixed):** чёткое разделение типов транзакций для точного расчёта свободных средств.

**Фиксированные категории в плане:** позволяет автоматически классифицировать транзакции по категории, даже если флаг не проставлен.

**Disposable income как ключевая метрика:** фокус на реально свободных деньгах, которыми пользователь может управлять.

**Выбор базы для сбережений (savings_base):** позволяет пользователю выбрать стратегию — амбициозную (от net income, мотивирует оптимизировать фиксы) или реалистичную (от disposable, когда фиксы неизменяемы). Оба подхода валидны в разных жизненных ситуациях.

**Период как ключ кэша:** естественное разбиение данных, эффективная инвалидация.

**Адаптивное именование файлов планов:** поддержка разных интервалов без изменения логики.

---

## 15. Примечания для разработки

### 15.1 Приоритеты при реализации

1. Корректность расчётов важнее производительности на этапе MVP.
2. Читаемость кода важнее краткости.
3. Идемпотентность операций — обязательное требование.
4. Все пользовательские сообщения должны быть понятны без чтения документации.

### 15.2 Соглашения по коду

- Type hints обязательны для всех публичных функций и методов.
- Docstrings в формате Google style.
- Тесты для каждого нового модуля.
- Логирование через стандартный `logging` модуль.

### 15.3 Рекомендации по тестированию

- Использовать `pytest` с fixtures.
- In-memory SQLite для unit-тестов репозиториев.
- Временные директории для интеграционных тестов workspace.
- Параметризованные тесты для разных типов интервалов.
