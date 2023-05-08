/* SPDX-License-Identifier: BSD-3-Clause */

#include "core.h"
#include "srx_module.h"

static struct confd confd;

static int startup_save_hook(sr_session_ctx_t *session, uint32_t sub_id, const char *module,
	const char *xpath, sr_event_t event, unsigned request_id, void *priv)
{
	if (systemf("sysrepocfg -X/cfg/startup-config.cfg -d startup -f json"))
		return SR_ERR_SYS;

	return SR_ERR_OK;
}

static int commit_done_hook(sr_session_ctx_t *session, uint32_t sub_id, const char *module,
	const char *xpath, sr_event_t event, unsigned request_id, void *priv)
{
	/* No need to reload if the system is still bootstrapping. */
	if (system("runlevel >/dev/null"))
		return SR_ERR_OK;

	if (system("initctl -nbq reload"))
		return SR_ERR_SYS;

	return SR_ERR_OK;
}

static const struct srx_module_requirement core_reqs[] = {
	{ .dir = YANG_PATH_, .name = "kernelkit-infix-deviations", .rev = "2023-04-03" },

	{ NULL }
};

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

	rc = ietf_interfaces_init(&confd);
	if (rc)
		goto err;
	rc = ietf_system_init(&confd);
	if (rc)
		goto err;

	/* YOUR_INIT GOES HERE */

	/* Set up hook to save startup-config to persisten backend store */
	rc = sr_session_start(confd.conn, SR_DS_STARTUP, &startup);
	if (rc)
		goto err;

	rc = sr_module_change_subscribe(startup, "ietf-system", "/ietf-system:system//.",
					startup_save_hook, NULL, 0, SR_SUBSCR_PASSIVE | SR_SUBSCR_DONE_ONLY, &confd.sub);
	if (rc) {
		ERROR("failed setting up startup-config hook: %s", sr_strerror(rc));
		goto err;
	}

	rc = sr_module_change_subscribe(session, "ietf-system", "/ietf-system:system//.",
					commit_done_hook, NULL, 0, SR_SUBSCR_PASSIVE | SR_SUBSCR_DONE_ONLY, &confd.sub);
	if (rc) {
		ERROR("failed setting up startup-config hook: %s", sr_strerror(rc));
		goto err;
	}

	rc = sr_module_change_subscribe(session, "ietf-interfaces", "/ietf-interfaces:interfaces//.",
					commit_done_hook, NULL, 0, SR_SUBSCR_PASSIVE | SR_SUBSCR_DONE_ONLY, &confd.sub);
	if (rc) {
		ERROR("failed setting up startup-config hook: %s", sr_strerror(rc));
		goto err;
	}

	rc = srx_require_modules(confd.conn, core_reqs);
	if (rc)
		goto err;

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
