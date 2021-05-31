INFRA_API = 'entity/infrastructure/hosts'
FETCH_APPLICATIONS = "entity/applications/"
FETCH_SYN_APPLICATIONS = "synthetic/monitors"
APP_BILLING_API = "metrics/query?metricSelector=builtin%3Abilling.apps.web.sessionsWithoutReplayByApplication%3Afold&from=now-120m"
SYN_BILLING_API = "metrics/query?metricSelector=builtin%3Abilling.synthetic.actions%3Afold&from=now-120m"
HTTP_BILLING_API = "metrics/query?metricSelector=builtin%3Abilling.synthetic.requests%3Afold&from=now-120m"
APP_BILLING_API_REPLAY = "metrics/query?metricSelector=builtin%3Abilling.apps.web.sessionsWithReplayByApplication%3Afold&from=now-120m"
