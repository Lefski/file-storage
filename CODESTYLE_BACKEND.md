# 1. Отступы
Рекомендуется использовать 1 таб на каждый уровень отступа. Python 3 запрещает смешивание табуляции и пробелов в отступах. Код, в котором используются и те, и другие типы отступов, должен быть исправлен так, чтобы отступы в нем были расставлены только с помощью табов.

<span style="color:green">Хорошо</span>
```
def tab_using():
    one_tab_using = 'Using 1 tab'
```
<span style="color:red">Плохо</span>
```
def no_tab():
    4spaces_using = 'Ugly'
```

# 2. Точки с запятой
Не разделяйте ваши строки с помощью точек с запятой и не используйте точки с запятой для разделения команд, находящихся на одной строке.

<span style="color:green">Хорошо</span>
```
a = 'String'
b = 15
c = 7.2
```
<span style="color:red">Плохо</span>
```
a = 'String';
b = 15; c = 7.2;
```

# 3. Скобки
Используйте скобки экономно. Не используйте их с выражением return или с условной конструкцией, если не требуется организовать перенос строки. Однако скобки хорошо использовать для создания кортежей.

<span style="color:green">Хорошо</span>
```
if budget < 0:
    return False
# -------------------
while counter <= 10:
    counter += 1
# -------------------
if sea_country and cheap_country:
    add_country_for_visit()
# -------------------
if not line:
    continue
# -------------------
return result
# -------------------
for (key, value) in dict.items(): ...
```
<span style="color:red">Плохо</span>
```
if (budget < 0):
    return (False)
# -------------------
if not(line):
    continue
# -------------------
return (result)
```
# 4. Пробелы в выражениях и инструкциях
## 4.1 Пробелы и скобки

### 4.1.1 Не ставьте пробелы внутри каких-либо скобок (обычных, фигурных и квадратных).

<span style="color:green">Хорошо</span>
```
pineapple(pine[1], {apple: 2})
```
<span style="color:red">Плохо</span>
```
pineapple( pine[ 1 ], { apple: 2 } )
```
### 4.1.2 Никаких пробелов перед открывающей скобкой, которая начинает список аргументов, индекс или срез.

<span style="color:green">Хорошо</span>
```
get_number_of_guests(1)
```
<span style="color:red">Плохо</span>
```
get_number_of_guests (1)
```
<span style="color:green">Хорошо</span>
```
dish['ingredients'] = cook_book[:3]
```
<span style="color:red">Плохо</span>
```
dish ['ingredients'] = cook_book [:3]
```
## 4.2 Пробелы рядом с запятой, точкой с запятой и точкой

### 4.2.1 Перед запятой, точкой с запятой либо точкой не должно быть никаких пробелов. Используйте пробел после запятой, точки с запятой или точки (кроме того случая, когда они находятся в конце строки).

<span style="color:green">Хорошо</span>
```
if number_of_goods == 4:
    print(number_of_goods, total_price)
```
<span style="color:red">Плохо</span>
```
if number_of_goods == 4 :
    print(number_of_goods , total_price)
```
## 4.3 Пробелы вокруг бинарных операторов

### 4.3.1 Окружайте бинарные операторы одиночными пробелами с каждой стороны. Это касается присваивания (=), операторов сравнения (==, <, >, !=, <>, <=, >=, in, not in, is, is not), и булевых операторов (and, or, not). Используйте, как вам покажется правильным, окружение пробелами по отношению к арифметическим операторам, но расстановка пробелов по обеим сторонам бинарного оператора придает целостность коду.

<span style="color:green">Хорошо</span>
```
counter == 1
```
<span style="color:red">Плохо</span>
```
counter<1
```
### 4.3.2 Не используйте более одного пробела вокруг оператора присваивания (или любого другого оператора) для того, чтобы выровнять его с другим.

<span style="color:green">Хорошо</span>
```
price = 1000
price_with_taxes = 1200
price_with_taxes_and_discounts = 1100
```
<span style="color:red">Плохо</span>
```
price                          = 1000
price_with_taxes               = 1200
price_with_taxes_and_discounts = 1100
```
### 4.3.3 Не используйте пробелы по сторонам знака =, когда вы используете его, чтобы указать на именованный аргумент или значение по умолчанию.

<span style="color:green">Хорошо</span>
```
def complex(real, imag=0.0): return magic(r=real, i=imag)
```
<span style="color:red">Плохо</span>
```
def complex(real, imag = 0.0): return magic(r = real, i = imag)
```

# 5. Длина строк
Ограничивайте длину строк 79 символами (а длину строк документации и комментариев — 72 символами). В общем случае не используйте обратный слеш в качестве перехода на новую строку. Используйте доступное в Python явное объединение строк посредством круглых и фигурных скобок. Если необходимо, можно добавить дополнительную пару скобок вокруг выражения.

<span style="color:green">Хорошо</span>
```
style_object(self, width, height, color='black', design=None,
            emphasis=None, highlight=0)

if (width == 0 and height == 0 and
    color == 'red' and emphasis == 'strong'):
```
Если ваш текст не помещается в одну строку, используйте скобки для явного объединения строк.

<span style="color:green">Хорошо</span>
```
long_string = ('This will build a very long long '
            'long long long long long long string')
```
Что касается длинных URL в комментариях, то располагайте их, если это необходимо, на одной строке.

<span style="color:green">Хорошо</span>
```
# See details at
# http://www.example.com/example/example/example/example/example/example/example_example.html
```
<span style="color:red">Плохо</span>
```
# See details at
# http://www.example.com/example/example/example/example/example/\
# example/example_example.html
```
Обратный слеш иногда используется. Например, с длинной конструкцией with для переноса блока инструкций.

<span style="color:green">Хорошо</span>
```
with open('/path/to/some/file/you/want/to/read') as file_1, \
     open('/path/to/some/file/being/written', 'w') as file_2:
    file_2.write(file_1.read())
```
Ещё один подобный случай — длинные assert.

# 6. Пустые строки
Отделяйте функции (верхнего уровня, не функции внутри функций) и определения классов двумя пустыми строками. Определения методов внутри класса отделяйте одной пустой строкой. Две пустые строки должны быть между объявлениями верхнего уровня, будь это класс или функция. Одна пустая строка должна быть между определениями методов и между объявлением класса и его первым методом.
```
import os
.
.
class MyClass:
.
def __init__(self):
  self.name = 'My name'
  .
  def f(self):
    return 'hello world'
  .
  .
def MyFunc():
i = 12345
return i
.
myclass = MyClass()
```
Используйте (без энтузиазма) пустые строки в коде функций, чтобы отделить друг от друга логические части.

Python расценивает символ control+L как незначащий (whitespace), и вы можете использовать его, потому что многие редакторы обрабатывают его как разрыв страницы — таким образом, логические части в файле будут на разных страницах. Однако не все редакторы распознают control+L и могут на его месте отображать другой символ.

# 7. Имена
Имена, которых следует избегать:

Односимвольные имена, исключая счетчики либо итераторы. Никогда не используйте символы l (маленькая латинская буква «эль»), O (заглавная латинская буква «о») или I (заглавная латинская буква «ай») как однобуквенные идентификаторы. В некоторых шрифтах эти символы неотличимы от цифры один и нуля. Если очень нужно l, пишите вместо неё заглавную L.
<span style="color:green">Хорошо</span>
long_name = 'Хорошее имя переменной'
L = 'Допустимо, но лучше избегать'
<span style="color:red">Плохо</span>
```
l = 1
I = 1
O = 0
```
Дефисы и подчеркивания в именах модулей и пакетов.

<span style="color:green">Хорошо</span>
```
import my_module
```
<span style="color:red">Плохо</span>
```
import my-module
```
Двойные подчеркивания (в начале и конце имен) зарезервированы для языка.

<span style="color:green">Хорошо</span>
```
my_variable = 'Variable'
```
<span style="color:red">Плохо</span>
```
__myvariable__ = 'Variable'
```
## 7.1 Имена функций
Имена функций должны состоять из маленьких букв, а слова разделяться символами подчеркивания — это необходимо, чтобы увеличить читабельность.

<span style="color:green">Хорошо</span>
```
my_variable = 'Variable'
```
<span style="color:red">Плохо</span>
```
My-Variable = 'Variable'
```
Стиль mixedCase допускается в тех местах, где уже преобладает такой стиль — для сохранения обратной совместимости.

## 7.2 Имена модулей и пакетов
Модули должны иметь короткие имена, состоящие из маленьких букв. Можно использовать символы подчёркивания, если это улучшает читабельность. То же самое относится и к именам пакетов, однако в именах пакетов не рекомендуется использовать символ подчёркивания.

Так как имена модулей отображаются в имена файлов, а некоторые файловые системы являются нечувствительными к регистру символов и обрезают длинные имена, очень важно использовать достаточно короткие имена модулей — это не проблема в Unix, но, возможно, код окажется непереносимым в старые версии Windows, Mac, или DOS.

<span style="color:green">Хорошо</span>
```
import vkapi
```
<span style="color:red">Плохо</span>
```
import My-First-VKontakte-API-Modul
```
## 7.3 Имена классов
Все имена классов должны следовать соглашению CapWords почти без исключений.
```
class MyFirstClass:
```
Иногда вместо этого могут использоваться соглашения для именования функций, если интерфейс документирован и используется в основном как функции.

Обратите внимание, что существуют отдельных соглашения о встроенных именах: большинство встроенных имен — одно слово (либо два слитно написанных слова), а соглашение CapWords используется только для именования исключений и встроенных констант.

Так как исключения являются классами, к исключениями применяется стиль именования классов. Однако вы можете добавить Error в конце имени (если, конечно, исключение действительно является ошибкой).

## 7.4 Имена констант

Константы обычно объявляются на уровне модуля и записываются только заглавными буквами, а слова разделяются символами подчеркивания.
```
MAX_OVERFLOW = 10
TOTAL = 100
```
# 8. Комментарии
Комментарии, противоречащие коду, хуже, чем отсутствие комментариев. Всегда исправляйте комментарии, если меняете код!

Комментарии должны быть законченными предложениями. Если комментарий — фраза или предложение, первое слово должно быть написано с большой буквы, если только это не имя переменной, которая начинается с маленькой буквы (никогда не отступайте от этого правила для имен переменных).

Ставьте два пробела после точки в конце предложения.

Если вы — программист, не говорящий по-английски, то всё равно следует использовать английский язык для написания комментариев. Особенно, если нет уверенности на 120% в том, что этот код будут читать только люди, говорящие на вашем родном языке.

## 8.1 Блоки комментариев
Блок комментариев обычно объясняет код (весь или только некоторую часть), идущий после блока, и должен иметь тот же отступ, что и сам код. Каждая строчка такого блока должна начинаться с символа # и одного пробела после него (если только сам текст комментария не имеет отступа).

Абзацы внутри блока комментариев разделяются строкой, состоящей из одного символа #.

## 8.2 Комментарии в строке с кодом
Старайтесь реже использовать подобные комментарии.

Такой комментарий находится в той же строке, что и инструкция. «Встрочные» комментарии должны отделяться хотя бы двумя пробелами от инструкции. Они должны начинаться с символа # и одного пробела.

Комментарии в строке с кодом не нужны и только отвлекают от чтения, если они объясняют очевидное.

<span style="color:red">Плохо</span>
```
counter = counter + 1                 # Increment counter
```
## 8.3 Строки документации
Соглашения о написании хорошей документации (docstrings) зафиксированы в PEP 257.

Пишите документацию для всех публичных модулей, функций, классов, методов. Строки документации необязательны для приватных методов, но лучше написать, что делает метод. Комментарий нужно писать после строки с def.

Очень важно, чтобы закрывающие кавычки стояли на отдельной строке. А еще лучше, если перед ними будет ещё и пустая строка.

<span style="color:green">Хорошо</span>
```
"""Return something useful

Optional plotz says to frobnicate the bizbaz first.

"""
```
Для однострочной документации можно оставить """ на той же строке.

# 9. Циклы
## 9.1 Циклы по спискам
Если нам необходимо в цикле пройти по всем элементам списка, то хорошим тоном (да и более читаемым) будет такой способ:

<span style="color:green">Хорошо</span>
```
colors = ['red', 'green', 'blue', 'yellow']
for color in colors:
    print(color)
```
И хотя бывалые программисты или просто любители C могут использовать и такой код, это моветон.

<span style="color:red">Плохо</span>
```
colors = ['red', 'green', 'blue', 'yellow']
for i in range(len(colors)):
    print(colors[i])
```
А если нужно пройти по списку задом наперед, то лучше всего использовать метод reversed:

<span style="color:green">Хорошо</span>
```
colors = ['red', 'green', 'blue', 'yellow']
for color in reversed(colors):
    print(color)
```
Вместо того чтобы писать избыточный код, который и читается-то не очень внятно.

<span style="color:red">Плохо</span>
```
colors = ['red', 'green', 'blue', 'yellow']
for i in range(len(colors)-1, -1, -1):
    print(colors[i])
```
## 9.2 Циклы по списку чисел
Если есть необходимость пройти в цикле по ряду чисел, то метод range будет намного приемлемее, как минимум потому, что этот метод потребляет намного меньше памяти, чем вариант в блоке "Плохо". А представьте, что у вас ряд из трёх миллиардов последовательных чисел!

<span style="color:green">Хорошо</span>
```
for i in range(6):
    print(i**2)
Плохо
for i in [0, 1, 2, 3, 4, 5]:
    print(i**2)
```
## 9.3 Циклы по спискам с индексами
Метод enumerate позволяет получить сразу индекс и значение из списка, что, во-первых, предоставляет множество возможностей для дальшнейшего проектирования, а во-вторых, такой код легче читается и воспринимается.

<span style="color:green">Хорошо</span>
```
colors = ['red', 'green', 'blue', 'yellow']
for i, color in enumerate(colors):
    print(i, '-->', color)
```
<span style="color:red">Плохо</span>
```
colors = ['red', 'green', 'blue', 'yellow']
for i in range(len(colors)):
    print(i, '-->', colors[i])
```
## 9.4 Циклы по двум спискам
Используя метод zip, мы получаем из двух списков один список кортежей, что более удобно для дальнейшего использования и требует меньше памяти. Да и просто этот вариант более элегантный.

<span style="color:green">Хорошо</span>
```
names = ['raymond', 'rachel', 'matthew']
colors = ['red', 'green', 'blue', 'yellow']
for name, color in zip(names, colors):
    print(name, '-->', color)
```
<span style="color:red">Плохо</span>
```
names = ['raymond', 'rachel', 'matthew']
colors = ['red', 'green', 'blue', 'yellow']
n = min(len(names), len(colors))
for i in range(n):
    print(names[i], '-->', colors[i])
```
# 10. Импорты
Каждый импорт, как правило, должен быть на отдельной строке.

<span style="color:green">Хорошо</span>
```
import os
import sys
```
<span style="color:red">Плохо</span>
```
import sys, os
```
В то же время, можно писать так:

<span style="color:green">Хорошо</span>
```
from subprocess import Popen, PIPE
```
Импорты всегда располагаются в начале файла, сразу после комментариев уровня модуля, строк документации, перед объявлением констант и объектов уровня модуля. Импорты должны быть сгруппированы в порядке от самых простых до самых сложных:

    импорты из стандартной библиотеки,
    сторонние импорты,
    импорты из библиотек вашего приложения.
Наряду с группированием, импорты должны быть отсортированы лексикографически, нерегистрозависимо, согласно полному пути до каждого модуля.

<span style="color:green">Хорошо</span>
```
import foo
from foo import bar
from foo.bar import baz
from foo.bar import Quux
from Foob import ar
```
Рекомендуется абсолютное импортирование, так как оно обычно более читаемо и ведет себя лучше (или, по крайней мере, даёт понятные сообщения об ошибках), если импортируемая система настроена неправильно (например, когда каталог внутри пакета заканчивается на sys.path).

<span style="color:green">Хорошо</span>
```
import mypkg.sibling
from mypkg import sibling
from mypkg.sibling import example
```
Тем не менее, явный относительный импорт является приемлемой альтернативой абсолютному импорту, особенно при работе со сложными пакетами, где использование абсолютного импорта было бы излишне подробным.

<span style="color:green">Хорошо</span>
```
from . import sibling
from .sibling import example
```
Следует избегать шаблонов импортов (from import *), так как они делают неясным то, какие имена присутствуют в глобальном пространстве имён, что вводит в заблуждение как читателей, так и многие автоматизированные средства.

# 11. Информативные имена переменных, функций и классов

## 11.1 Общие принципы именования

Имена должны четко отражать назначение и содержание переменной/функции/класса.

<span style="color:green">Хорошо</span>
```
# Переменные
user_age = 25
is_logged_in = True
MAX_CONNECTIONS = 10

# Функции
def calculate_total_price(items):
    pass

def validate_user_credentials(username, password):
    pass

# Классы
class UserAccountManager:
    pass

class DatabaseConnectionPool:
    pass
```

<span style="color:red">Плохо</span>
```
# Неясные имена
a = 25
flag = True
x = 10

# Неинформативные функции
def calc(x):
    pass

def check(a, b):
    pass

# Расплывчатые классы
class Manager:
    pass

class Processor:
    pass
```

## 11.2 Контекстно-зависимые имена

Имена должны соответствовать предметной области.

<span style="color:green">Хорошо</span>
```
class ShoppingCart:
    def add_product(self, product: Product, quantity: int) -> None:
        pass
    
    def calculate_subtotal(self) -> float:
        pass

class HTTPRequestHandler:
    def send_get_request(self, url: str, headers: dict) -> Response:
        pass
```

# 12. Модульный подход к разработке

## 12.1 Разделение ответственности

Каждый модуль должен решать одну конкретную задачу.

## 12.2 Структура модуля

Каждый модуль должен иметь четкий интерфейс.

<span style="color:green">Хорошо</span>

```
# services/payment_service.py
"""
Модуль для обработки платежей
"""

class PaymentProcessor:
    """Обработчик платежных операций"""
    
    def process_credit_card_payment(self, card_data: dict, amount: float) -> bool:
        """Обработать платеж по кредитной карте"""
        pass
    
    def refund_payment(self, transaction_id: str) -> bool:
        """Вернуть средства"""
        pass

# Основной интерфейс модуля
def create_payment_processor(api_key: str) -> PaymentProcessor:
    """Фабрика для создания обработчика платежей"""
    return PaymentProcessor(api_key)
```

# 13. SOLID-принципы

13.1 Single Responsibility Principle (SRP)

Класс должен иметь только одну причину для изменения.

<span style="color:green">Хорошо</span>

```
class UserAuthenticator:
    """Отвечает только за аутентификацию"""
    
    def authenticate(self, username: str, password: str) -> bool:
        pass
    
    def generate_token(self, user_id: int) -> str:
        pass

class UserDataManager:
    """Отвечает только за управление данными пользователя"""
    
    def save_user(self, user: User) -> None:
        pass
    
    def get_user_by_id(self, user_id: int) -> User:
        pass
```

<span style="color:red">Плохо</span>

```
class UserManager:
    """Нарушает SRP - делает слишком много"""
    
    def authenticate(self, username: str, password: str) -> bool:
        pass
    
    def save_user(self, user: User) -> None:
        pass
    
    def send_email(self, user: User, message: str) -> None:
        pass
    
    def generate_report(self) -> Report:
        pass
```

## 13.2 Open/Closed Principle (OCP)

Классы должны быть открыты для расширения, но закрыты для модификации.

<span style="color:green">Хорошо</span>

```
from abc import ABC, abstractmethod

class NotificationService(ABC):
    """Абстрактный базовый класс для служб уведомлений"""
    
    @abstractmethod
    def send(self, message: str, recipient: str) -> bool:
        pass

class EmailNotificationService(NotificationService):
    def send(self, message: str, recipient: str) -> bool:
        # Реализация отправки email
        return True

class SMSNotificationService(NotificationService):
    def send(self, message: str, recipient: str) -> bool:
        # Реализация отправки SMS
        return True

class PushNotificationService(NotificationService):
    def send(self, message: str, recipient: str) -> bool:
        # Реализация push-уведомлений
        return True
```

## 13.3 Liskov Substitution Principle (LSP)

Подтипы должны быть заменяемы для своих базовых типов.

<span style="color:green">Хорошо</span>

```
class Bird:
    def make_sound(self) -> str:
        return "Some bird sound"

class Sparrow(Bird):
    def make_sound(self) -> str:
        return "Chirp chirp"

class Eagle(Bird):
    def make_sound(self) -> str:
        return "Screech"

def demonstrate_bird_sounds(birds: list[Bird]) -> None:
    for bird in birds:
        print(bird.make_sound())

# Все подтипы могут быть использованы вместо базового класса
birds = [Sparrow(), Eagle(), Bird()]
demonstrate_bird_sounds(birds)
```

## 13.4 Interface Segregation Principle (ISP)

Много специализированных интерфейсов лучше, чем один универсальный.

<span style="color:green">Хорошо</span>

```
from abc import ABC, abstractmethod

class ReadableRepository(ABC):
    @abstractmethod
    def get_by_id(self, id: int):
        pass
    
    @abstractmethod
    def get_all(self) -> list:
        pass

class WritableRepository(ABC):
    @abstractmethod
    def save(self, entity) -> None:
        pass
    
    @abstractmethod
    def delete(self, id: int) -> None:
        pass

class UserRepository(ReadableRepository, WritableRepository):
    """Реализует только нужные интерфейсы"""
    
    def get_by_id(self, id: int):
        pass
    
    def get_all(self) -> list:
        pass
    
    def save(self, entity) -> None:
        pass
    
    def delete(self, id: int) -> None:
        pass
```

## 13.5 Dependency Inversion Principle (DIP)

Зависимости на абстракциях, а не на конкретных реализациях.

<span style="color:green">Хорошо</span>

```
from abc import ABC, abstractmethod

class Database(ABC):
    """Абстракция базы данных"""
    
    @abstractmethod
    def execute_query(self, query: str) -> list:
        pass

class MySQLDatabase(Database):
    """Конкретная реализация для MySQL"""
    
    def execute_query(self, query: str) -> list:
        # Реализация для MySQL
        pass

class PostgreSQLDatabase(Database):
    """Конкретная реализация для PostgreSQL"""
    
    def execute_query(self, query: str) -> list:
        # Реализация для PostgreSQL
        pass

class UserService:
    """Сервис зависит от абстракции, а не от конкретной реализации"""
    
    def __init__(self, database: Database):
        self.database = database
    
    def get_users(self) -> list:
        return self.database.execute_query("SELECT * FROM users")
```

# 14. Работа с внешними API и сервисами

## 14.1 Абстракция внешних API

Создавайте абстракции для работы с внешними сервисами.

<span style="color:green">Хорошо</span>

```
from abc import ABC, abstractmethod
import requests
from typing import Optional, Dict, Any

class WeatherAPI(ABC):
    """Абстрактный интерфейс для Weather API"""
    
    @abstractmethod
    def get_current_weather(self, city: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_forecast(self, city: str, days: int) -> Dict[str, Any]:
        pass

class OpenWeatherMapService(WeatherAPI):
    """Реализация для OpenWeatherMap API"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openweathermap.org"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_current_weather(self, city: str) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/data/2.5/weather"
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise WeatherAPIError(f"Failed to fetch weather data: {e}")
    
    def get_forecast(self, city: str, days: int) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/data/2.5/forecast"
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric',
            'cnt': days * 8  # OpenWeatherMap uses 3-hour intervals
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise WeatherAPIError(f"Failed to fetch forecast: {e}")

class WeatherAPIError(Exception):
    """Специализированное исключение для ошибок API погоды"""
    pass
```

## 14.2 Обработка ошибок и повторные попытки

<span style="color:green">Хорошо</span>

```
import time
from typing import Callable, Any

class APIRetryHandler:
    """Обработчик повторных попыток для API запросов"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def execute_with_retry(self, api_call: Callable[[], Any]) -> Any:
        """Выполнить API вызов с повторными попытками"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return api_call()
            except (requests.RequestException, WeatherAPIError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    time.sleep(sleep_time)
                    continue
                else:
                    raise last_exception

# Использование
retry_handler = APIRetryHandler(max_retries=3, backoff_factor=1.0)

def get_weather_safely(service: WeatherAPI, city: str) -> Dict[str, Any]:
    return retry_handler.execute_with_retry(
        lambda: service.get_current_weather(city)
    )
```

## 14.3 Кэширование и ограничение запросов

<span style="color:green">Хорошо</span>

```
import time
from functools import wraps
from typing import Dict, Any

class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def acquire(self) -> bool:
        current_time = time.time()
        
        # Удаляем старые запросы
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        return False
    
    def wait_until_available(self) -> None:
        while not self.acquire():
            time.sleep(0.1)

def rate_limit(max_requests: int, time_window: int):
    """Декоратор для ограничения частоты запросов"""
    limiter = RateLimiter(max_requests, time_window)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait_until_available()
            return func(*args, **kwargs)
        return wrapper
    return decorator

class CachedWeatherService(WeatherAPI):
    """Сервис погоды с кэшированием"""
    
    def __init__(self, weather_service: WeatherAPI, cache_ttl: int = 300):
        self.weather_service = weather_service
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
    
    @rate_limit(max_requests=60, time_window=60)  # 60 запросов в минуту
    def get_current_weather(self, city: str) -> Dict[str, Any]:
        current_time = time.time()
        
        # Проверяем кэш
        if city in self._cache:
            cache_time, data = self._cache[city]
            if current_time - cache_time < self.cache_ttl:
                return data
        
        # Получаем свежие данные
        data = self.weather_service.get_current_weather(city)
        self._cache[city] = (current_time, data)
        return data
    
    def get_forecast(self, city: str, days: int) -> Dict[str, Any]:
        return self.weather_service.get_forecast(city, days)
```