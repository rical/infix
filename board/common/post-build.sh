#!/bin/sh
# shellcheck disable=SC1090,SC1091
common=$(dirname "$(readlink -f "$0")")
. "$BR2_CONFIG" 2>/dev/null
. "$TARGET_DIR/usr/lib/os-release"

if [ -n "${ID_LIKE}" ]; then
    ID="${ID} ${ID_LIKE}"
fi

if [ -z "$GIT_VERSION" ]; then
    infix_path="$BR2_EXTERNAL_INFIX_PATH"
    if [ -n "$INFIX_OEM_PATH" ]; then
	# Use version from br2-external OEM:ing Infix
	infix_path="$INFIX_OEM_PATH"
    fi
    GIT_VERSION=$(git -C "$infix_path" describe --always --dirty --tags)
fi

# Override VERSION in /etc/os-release and filenames for release builds
if [ -n "$INFIX_RELEASE" ]; then
    VERSION="$INFIX_RELEASE"
else
    VERSION=$GIT_VERSION
fi

# This is a symlink to /usr/lib/os-release, so we remove this to keep
# original Buildroot information.
rm -f "$TARGET_DIR/etc/os-release"
{
    echo "NAME=\"$INFIX_NAME\""
    echo "ID=$INFIX_ID"
    echo "PRETTY_NAME=\"$INFIX_TAGLINE $VERSION\""
    echo "ID_LIKE=\"${ID}\""
    echo "VERSION=\"${VERSION}\""
    echo "VERSION_ID=${VERSION}"
    echo "BUILD_ID=\"${GIT_VERSION}\""
    if [ -n "$INFIX_IMAGE_ID" ]; then
	echo "IMAGE_ID=\"$INFIX_IMAGE_ID\""
    fi
    if [ -n "$INFIX_RELEASE" ]; then
	echo "IMAGE_VERSION=\"$INFIX_RELEASE\""
    fi
    echo "ARCHITECTURE=\"${INFIX_ARCH}\""
    echo "HOME_URL=$INFIX_HOME"
    if [ -n "$INFIX_VENDOR" ]; then
	echo "VENDOR_NAME=\"$INFIX_VENDOR\""
    fi
    if [ -n "$INFIX_VENDOR_HOME" ]; then
	echo "VENDOR_HOME=\"$INFIX_VENDOR_HOME\""
    fi
    if [ -n "$INFIX_DOC" ]; then
	echo "DOCUMENTATION_URL=\"$INFIX_DOC\""
    fi
    if [ -n "$INFIX_SUPPORT" ]; then
	echo "SUPPORT_URL=\"$INFIX_SUPPORT\""
    fi
    if [ -n "$INFIX_DESC" ]; then
	echo "INFIX_DESC=\"$INFIX_DESC\""
    fi
} > "$TARGET_DIR/etc/os-release"

echo "$INFIX_TAGLINE $VERSION -- $(date +"%b %e %H:%M %Z %Y")" > "$TARGET_DIR/etc/version"

# Drop Buildroot default symlink to /tmp
if [ -L "$TARGET_DIR/var/lib/avahi-autoipd" ]; then
	rm    "$TARGET_DIR/var/lib/avahi-autoipd"
	mkdir "$TARGET_DIR/var/lib/avahi-autoipd"
fi

# Allow pdmenu (setup) and bash to be login shells, bash is added
# automatically when selected in menuyconfig, but not when BusyBox
# provides a symlink (for ash).  The /bin/{true,false} are old UNIX
# beart means of disabling a user.
grep -qsE '^/usr/bin/pdmenu$$' "$TARGET_DIR/etc/shells" \
        || echo "/usr/bin/pdmenu" >> "$TARGET_DIR/etc/shells"
grep -qsE '^/bin/bash$$' "$TARGET_DIR/etc/shells" \
        || echo "/bin/bash" >> "$TARGET_DIR/etc/shells"
grep -qsE '^/bin/true$$' "$TARGET_DIR/etc/shells" \
        || echo "/bin/true" >> "$TARGET_DIR/etc/shells"
grep -qsE '^/bin/false$$' "$TARGET_DIR/etc/shells" \
        || echo "/bin/false" >> "$TARGET_DIR/etc/shells"

# Allow clish (symlink to /usr/bin/klish) to be a login shell
grep -qsE '^/bin/clish$$' "$TARGET_DIR/etc/shells" \
        || echo "/bin/clish" >> "$TARGET_DIR/etc/shells"

if [ -n "$BR2_PACKAGE_NGINX" ]; then
    cp "$common/netbrowse.conf" "$TARGET_DIR/etc/nginx/"
    cp "$common/nginx.conf" "$TARGET_DIR/etc/nginx/"
    ln -sf ../available/nginx.conf "$TARGET_DIR/etc/finit.d/enabled/nginx.conf"

    cat <<EOF > "$TARGET_DIR/etc/avahi/services/http.service"
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h</name>
  <service>
    <type>_http._tcp</type>
    <port>80</port>
    <txt-record value-format="text">product=$INFIX_NAME</txt-record>
  </service>
</service-group>
EOF
    cat <<EOF > "$TARGET_DIR/etc/avahi/services/https.service"
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h</name>
  <service>
    <type>_https._tcp</type>
    <port>443</port>
    <txt-record value-format="text">product=$INFIX_NAME</txt-record>
  </service>
</service-group>
EOF
fi
