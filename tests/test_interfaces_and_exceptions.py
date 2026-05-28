"""Tests for abstract interfaces and domain exception hierarchy."""

from abc import ABC

import pytest

from hgnc_xref_loader.exceptions import ConfigError, RepositoryError, ServiceError
from hgnc_xref_loader.repositories.base_repository import Repository
from hgnc_xref_loader.services.base_service import Service


class TestServiceABC:
    def test_service_is_abc(self):
        assert issubclass(Service, ABC)

    def test_service_has_run_abstract_method(self):
        assert hasattr(Service, "run")

    def test_service_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Service()  # type: ignore[abstract]

    def test_concrete_service_can_be_instantiated(self):
        class ConcreteService(Service):
            def run(self) -> None:
                pass

        svc = ConcreteService()
        assert svc is not None

    def test_concrete_service_run_callable(self):
        class ConcreteService(Service):
            def run(self) -> None:
                pass

        svc = ConcreteService()
        svc.run()


class TestRepositoryABC:
    def test_repository_is_abc(self):
        assert issubclass(Repository, ABC)

    def test_repository_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Repository()  # type: ignore[abstract]

    def test_concrete_repository_can_be_instantiated(self):
        class ConcreteRepo(Repository):
            def health_check(self) -> bool:
                return True

        repo = ConcreteRepo()
        assert repo is not None


class TestExceptionHierarchy:
    def test_service_error_is_exception(self):
        assert issubclass(ServiceError, Exception)

    def test_config_error_is_service_error(self):
        assert issubclass(ConfigError, ServiceError)

    def test_repository_error_is_service_error(self):
        assert issubclass(RepositoryError, ServiceError)

    def test_service_error_can_be_raised(self):
        with pytest.raises(ServiceError):
            raise ServiceError("test")

    def test_config_error_can_be_raised(self):
        with pytest.raises(ServiceError):
            raise ConfigError("bad config")

    def test_repository_error_can_be_raised(self):
        with pytest.raises(ServiceError):
            raise RepositoryError("db error")

    def test_service_error_has_message(self):
        err = ServiceError("something broke")
        assert str(err) == "something broke"

    def test_config_error_caught_by_service_error(self):
        with pytest.raises(ServiceError):
            raise ConfigError("missing")

    def test_repository_error_caught_by_service_error(self):
        with pytest.raises(ServiceError):
            raise RepositoryError("conn failed")

    def test_config_and_repository_distinct(self):
        assert ConfigError is not RepositoryError


class TestServiceReceivesRepositoryViaDI:
    def test_service_accepts_repository_in_constructor(self):
        class ConcreteRepo(Repository):
            def health_check(self) -> bool:
                return True

        class ConcreteService(Service):
            def __init__(self, repository: Repository) -> None:
                self._repository = repository

            def run(self) -> None:
                pass

        repo = ConcreteRepo()
        svc = ConcreteService(repository=repo)
        assert svc._repository is repo
