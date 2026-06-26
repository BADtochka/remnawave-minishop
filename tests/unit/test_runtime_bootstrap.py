from bot.app.factories import runtime as runtime_factory
from bot.app.factories.runtime import RuntimeBootstrap, build_core_runtime


def test_build_core_runtime_uses_shared_bootstrap_for_plugin_context(monkeypatch) -> None:
    settings = object()
    session_factory = object()
    bot = object()
    i18n = object()
    service = object()
    calls = []

    class FakeCoreServices:
        def as_dict(self) -> dict[str, object]:
            return {"panel_service": service}

    def fake_build_core_services(
        settings_arg,
        bot_arg,
        session_factory_arg,
        i18n_arg,
        bot_username_arg,
    ):
        calls.append(
            (
                settings_arg,
                bot_arg,
                session_factory_arg,
                i18n_arg,
                bot_username_arg,
            )
        )
        return FakeCoreServices()

    monkeypatch.setattr(runtime_factory, "build_core_services", fake_build_core_services)

    bootstrap = RuntimeBootstrap(
        settings=settings,
        session_factory=session_factory,
        bot=bot,
        i18n=i18n,
    )
    core_runtime = build_core_runtime(bootstrap, bot_username="runtimebot")

    assert calls == [(settings, bot, session_factory, i18n, "runtimebot")]
    assert core_runtime.bootstrap is bootstrap
    assert core_runtime.plugin_context.settings is settings
    assert core_runtime.plugin_context.session_factory is session_factory
    assert core_runtime.plugin_context.bot is bot
    assert core_runtime.plugin_context.i18n is i18n
    assert core_runtime.services == {"panel_service": service}
