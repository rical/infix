AC_PREREQ(2.61)
AC_INIT([confd], [1.0.0], [https://github.com/kernelkit/infix/issues])
AM_INIT_AUTOMAKE(1.11 foreign subdir-objects)
AM_SILENT_RULES(yes)

AC_CONFIG_FILES([
	Makefile
	bin/Makefile
	share/Makefile
	share/factory.d/Makefile
	share/failure.d/Makefile
	src/Makefile
	yang/Makefile
])

AC_PROG_CC
AC_PROG_INSTALL
LT_INIT

AC_CONFIG_LIBOBJ_DIR(lib)
AC_REPLACE_FUNCS(vasprintf)
AC_REPLACE_FUNCS(asprintf)

# Check feature flags
AC_ARG_WITH(login-shell,
        AS_HELP_STRING([--with-login-shell=shell], [Login shell for new users, default: /bin/false]),
	[login_shell=$withval], [login_shell=yes])

AS_IF([test "x$with_login_shell" != "xno"], [
	AS_IF([test "x$login_shell" = "xyes"], [login_shell=/bin/false])
	AC_DEFINE_UNQUOTED(LOGIN_SHELL, "$login_shell", [Default: /bin/false])],[
	AC_DEFINE_UNQUOTED(LOGIN_SHELL, "/bin/false")])

# Check for pkg-config first, warn if it's not installed
PKG_PROG_PKG_CONFIG

PKG_CHECK_MODULES([augeas],  [augeas  >= 1.12.0])
PKG_CHECK_MODULES([glib],    [glib-2.0 >= 2.50 gio-2.0 gio-unix-2.0])
PKG_CHECK_MODULES([jansson], [jansson >= 2.0.0])
PKG_CHECK_MODULES([libite],  [libite >= 2.5.0])
PKG_CHECK_MODULES([sysrepo], [sysrepo >= 2.2.36])
PKG_CHECK_MODULES([libsrx],  [libsrx >= 1.0.0])

# Plugin installation path for sysrepo-plugind
PKG_CHECK_VAR([srpdplugindir], [sysrepo], [SRPD_PLUGINS_PATH])
AC_SUBST(srpdplugindir)

test "x$prefix" = xNONE && prefix=$ac_default_prefix
test "x$exec_prefix" = xNONE && exec_prefix='${prefix}'

DATAROOTDIR=`eval echo $datarootdir`
DATAROOTDIR=`eval echo $DATAROOTDIR`
AC_SUBST(DATAROOTDIR)

YANGDIR=`eval echo $datarootdir/yang/modules/confd`
AC_SUBST(YANGDIR)

LIBDIR=`eval echo $libdir`
LIBDIR=`eval echo $LIBDIR`
AC_SUBST(LIBDIR)

LOCALSTATEDIR=`eval echo $localstatedir`
LOCALSTATEDIR=`eval echo $LOCALSTATEDIR`
AC_SUBST(LOCALSTATEDIR)

RUNSTATEDIR=`eval echo $runstatedir`
RUNSTATEDIR=`eval echo $RUNSTATEDIR`
AC_SUBST(RUNSTATEDIR)

SYSCONFDIR=`eval echo $sysconfdir`
SYSCONFDIR=`eval echo $SYSCONFDIR`
AC_SUBST(SYSCONFDIR)

AC_OUTPUT
