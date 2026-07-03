D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\anyio\from_thread.py:118: SyntaxWarning: 'return' in a 'finally' block
  return result
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- D:\AI_Project\Dashboard_Share\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\AI_Project\Dashboard_Share
plugins: anyio-3.7.1
collecting ... collected 107 items / 1 error

=================================== ERRORS ====================================
________________________ ERROR collecting test_main.py ________________________
test_main.py:41: in <module>
    import main as app_module
main.py:3: in <module>
    from sqlalchemy.orm import Session
.venv\Lib\site-packages\sqlalchemy\__init__.py:13: in <module>
    from .engine import AdaptedConnection as AdaptedConnection
.venv\Lib\site-packages\sqlalchemy\engine\__init__.py:18: in <module>
    from . import events as events
.venv\Lib\site-packages\sqlalchemy\engine\events.py:19: in <module>
    from .base import Connection
.venv\Lib\site-packages\sqlalchemy\engine\base.py:30: in <module>
    from .interfaces import BindTyping
.venv\Lib\site-packages\sqlalchemy\engine\interfaces.py:38: in <module>
    from ..sql.compiler import Compiled as Compiled
.venv\Lib\site-packages\sqlalchemy\sql\__init__.py:14: in <module>
    from .compiler import COLLECT_CARTESIAN_PRODUCTS as COLLECT_CARTESIAN_PRODUCTS
.venv\Lib\site-packages\sqlalchemy\sql\compiler.py:61: in <module>
    from . import crud
.venv\Lib\site-packages\sqlalchemy\sql\crud.py:34: in <module>
    from . import dml
.venv\Lib\site-packages\sqlalchemy\sql\dml.py:34: in <module>
    from . import util as sql_util
.venv\Lib\site-packages\sqlalchemy\sql\util.py:46: in <module>
    from .ddl import sort_tables as sort_tables  # noqa: F401
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\sqlalchemy\sql\ddl.py:30: in <module>
    from .elements import ClauseElement
.venv\Lib\site-packages\sqlalchemy\sql\elements.py:808: in <module>
    class SQLCoreOperations(Generic[_T_co], ColumnOperators, TypingOnly):
C:\Users\Asus\AppData\Local\Python\pythoncore-3.14-64\Lib\typing.py:1175: in _generic_init_subclass
    super(Generic, cls).__init_subclass__(*args, **kwargs)
.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py:1988: in __init_subclass__
    raise AssertionError(
E   AssertionError: Class <class 'sqlalchemy.sql.elements.SQLCoreOperations'> directly inherits TypingOnly but has additional attributes {'__static_attributes__', '__firstlineno__'}.
=========================== short test summary info ===========================
ERROR test_main.py - AssertionError: Class <class 'sqlalchemy.sql.elements.SQ...
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 9.86s ===============================
