try:
	import pymysql
except ImportError:
	pass
else:
	pymysql.install_as_MySQLdb()
