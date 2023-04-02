/* SPDX-License-Identifier: BSD-3-Clause */

#include "core.h"

static struct confd confd;

static int startup_save_hook(sr_session_ctx_t *session, uint32_t sub_id, const char *module,
	const char *xpath, sr_event_t event, unsigned request_id, void *priv)
{
	if (run("sysrepocfg -X/cfg/startup-config.cfg -d startup -f json"))
		return SR_ERR_SYS;

	return SR_ERR_OK;
}

int sr_plugin_init_cb(sr_session_ctx_t *session, void **priv)
{
	sr_session_ctx_t *startup;
	int rc = SR_ERR_SYS;

	openlog("confd", LOG_USER, 0);

	/* Save context with default running config datastore for all our models */
	*priv = (void *)&confd;
	confd.session = session;
	confd.conn    = sr_session_get_connection(session);
	confd.sub     = NULL;

	if (!confd.conn)
		goto err;

	confd.aug = aug_init(NULL, "", 0);
	if (!confd.aug)
		goto err;

	if (rc = ietf_system_init(&confd))
		goto err;

	/* YOUR_INIT GOES HERE */

	/* Set up hook to save startup-config to persisten backend store */
	if (rc = sr_session_start(confd.conn, SR_DS_STARTUP, &startup))
		goto err;

	if (rc = sr_module_change_subscribe(startup, "ietf-system", "/ietf-system:system//.",
			startup_save_hook, NULL, 0, SR_SUBSCR_PASSIVE | SR_SUBSCR_DONE_ONLY, &confd.sub)) {
		ERROR("failed setting up startup-config hook: %s", sr_strerror(rc));
		goto err;
	}

	return SR_ERR_OK;
err:
	ERROR("init failed: %s", sr_strerror(rc));
	sr_unsubscribe(confd.sub);

	return rc;
}

void sr_plugin_cleanup_cb(sr_session_ctx_t *session, void *priv)
{
        sr_unsubscribe((sr_subscription_ctx_t *)priv);
	closelog();
}