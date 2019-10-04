import logging

import wiremind_kubernetes

logger = logging.getLogger(__name__)


def main():
    """
    postrollback will rollback, in case the release fails, manual actions that Helm doesn't manage, in this case
    it only make sure the pods we stopped in predeployment and postdeployment are scaled up.
    """
    deployment_manager = wiremind_kubernetes.KubernetesDeploymentManager()

    # Because start-pods is idempotent whe pods are already running, we prefer to try starting the pods
    # maybe some replicas were changed.
    # We prefer scaling up pods when they're already scaled up (it is idempotent; Kubernets Api is intelligent)
    # than missing scaling them up when they're all stopped.
    logger.debug("After Helm rollback, Trying to start pods ... ")
    deployment_manager.start_pods()


if __name__ == "__main__":
    main()
