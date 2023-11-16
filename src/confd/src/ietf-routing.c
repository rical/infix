/* SPDX-License-Identifier: BSD-3-Clause */

#include <srx/common.h>
#include <srx/lyx.h>
#include <srx/srx_module.h>
#include <srx/srx_val.h>

#include "core.h"

#define XPATH_BASE_ "/ietf-routing:routing"
#define XPATH_STATIC_ROUTES_ XPATH_BASE_ "/control-plane-protocols/control-plane-protocol"
#define STATICD_CONF "/etc/frr/staticd.conf"
#define STATICD_CONF_NEXT STATICD_CONF "+"
#define STATICD_CONF_PREV STATICD_CONF "-"
#define FRR_STATIC_CONFIG "! Generated by Infix\n\
frr defaults traditional\n \
hostname Router \n\
password zebra \n \
enable password zebra  \n \
log syslog informational \n"

static int parse_route(struct lyd_node *parent, FILE *fp)
{
	const char *outgoing_interface, *next_hop_address, *special_next_hop, *destination_prefix;
	struct lyd_node *next_hop;
	destination_prefix = lydx_get_cattr(parent, "destination-prefix");
	next_hop = lydx_get_child(parent, "next-hop");
	outgoing_interface = lydx_get_cattr(next_hop, "outgoing-interface");
	next_hop_address = lydx_get_cattr(next_hop, "next-hop-address");
	special_next_hop = lydx_get_cattr(next_hop, "special-next-hop");

	fprintf(fp, "ip route %s ", destination_prefix);

	/* There can only be one */
	if (outgoing_interface)
		fputs(outgoing_interface, fp);
	else if (next_hop_address)
		fputs(next_hop_address, fp);
	else if (strcmp(special_next_hop, "blackhole") == 0) {
		fputs("blackhole", fp);
	} else if (strcmp(special_next_hop, "unreachable") == 0) {
		fputs("reject", fp);
	} else if (strcmp(special_next_hop, "receive") == 0) {
		fputs("Null0", fp);
	}

	fputs("\n", fp);
	return SR_ERR_OK;
}

static int parse_static_routes(sr_session_ctx_t *session, struct lyd_node *parent, FILE *fp)
{
	struct lyd_node *ipv4, *v4routes, *route;
	int num_routes = 0;
	ipv4 = lydx_get_child(parent, "ipv4");

	v4routes = lydx_get_child(ipv4, "route");
	LY_LIST_FOR(v4routes, route)
	{
		parse_route(route, fp);
		num_routes++;
	}
	DEBUG("Found %d routes in configuration", num_routes);
	return num_routes;
}

static int change_control_plane_protocols(sr_session_ctx_t *session, uint32_t sub_id, const char *module,
                                          const char *xpath, sr_event_t event, unsigned request_id, void *priv)
{
	struct lyd_node *cplane, *tmp;
	int staticd_enabled = 0;
	int rc = SR_ERR_OK;
	sr_data_t *cfg;
	FILE *fp;

	switch (event) {
	case SR_EV_ENABLED: /* first time, on register. */
	case SR_EV_CHANGE: /* regular change (copy cand running) */
		fp = fopen(STATICD_CONF_NEXT, "w");
		if (!fp) {
			ERROR("Failed to open %s", STATICD_CONF_NEXT);
			return SR_ERR_INTERNAL;
		}
		fputs(FRR_STATIC_CONFIG, fp);
		break;

	case SR_EV_ABORT: /* User abort, or other plugin failed */
		remove(STATICD_CONF_NEXT);
		return SR_ERR_OK;

	case SR_EV_DONE:
		/* Check if passed validation in previous event */
		staticd_enabled = fexist(STATICD_CONF_NEXT);

		if (!staticd_enabled) {
			if (systemf("initctl -bfq disable staticd")) {
				ERROR("Failed to disable static routing daemon");
				rc = SR_ERR_INTERNAL;
				goto err_abandon;
			}
			/* Remove all generated files */
			remove(STATICD_CONF);
			return SR_ERR_OK;
		}
		remove(STATICD_CONF_PREV);
		rename(STATICD_CONF, STATICD_CONF_PREV);
		rename(STATICD_CONF_NEXT, STATICD_CONF);
		if (systemf("initctl -bfq status staticd")) {
			if (staticd_enabled) {
				if (systemf("initctl -bfq enable staticd")) {
					ERROR("Failed to enable static routing daemon");
					rc = SR_ERR_INTERNAL;
					goto err_abandon;
				}
			}
		} else {
			if (systemf("initctl -bfq restart zebra")) {
				ERROR("Failed to restart static routing daemon");
				rc = SR_ERR_INTERNAL;
				goto err_abandon;
			}
		}

		return SR_ERR_OK;
	default:
		return SR_ERR_OK;
	}

	rc = sr_get_data(session, "/ietf-routing:routing/control-plane-protocols//.", 0, 0, 0, &cfg);
	LY_LIST_FOR(lyd_child(cfg->tree), tmp)
	{
		LY_LIST_FOR(lyd_child(tmp), cplane)
		{
			const char *type;
			type = lydx_get_cattr(cplane, "type");
			if (!strcmp(type, "ietf-routing:static")) {
				staticd_enabled = parse_static_routes(session, lydx_get_child(cplane, "static-routes"), fp);
			}
		}
	}
	fclose(fp);

	if (!staticd_enabled)
		remove(STATICD_CONF_NEXT);
	sr_release_data(cfg);
err_abandon:
	return rc;
}

int ietf_routing_init(struct confd *confd)
{
	int rc = 0;
	REGISTER_CHANGE(confd->session, "ietf-routing", "/ietf-routing:routing/control-plane-protocols", 0, change_control_plane_protocols, confd, &confd->sub);
	return SR_ERR_OK;
fail:
	ERROR("Init routing failed: %s", sr_strerror(rc));
	return rc;
}
