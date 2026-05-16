import json

from app.core.config import Settings
from scripts.slack_notification_readiness import main, slack_notification_readiness


def _ready_settings(**overrides):
    values = {
        "_env_file": None,
        "slack_notifications_enabled": True,
        "slack_bot_token": "xoxb-secret-token",
        "slack_channel_lead_runs": "C123LEADRUNS",
        "slack_channel_hot_leads": "C123HOTLEADS",
        "slack_channel_instantly_replies": "C123REPLIES",
        "slack_channel_lease_option_inbound": "C123LEASEIN",
        "slack_channel_sms_calls": "C123SMSCALLS",
    }
    values.update(overrides)
    return Settings(**values)


def test_slack_notification_readiness_blocks_disabled_without_leaking_token() -> None:
    report = slack_notification_readiness(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=False,
            slack_bot_token="xoxb-secret-token",
            slack_channel_hot_leads="C123HOTLEADS",
        )
    )

    assert report["configured"] is False
    assert report["would_post"] is False
    assert "SLACK_NOTIFICATIONS_ENABLED=true" in report["missing"]
    rendered = json.dumps(report)
    assert "xoxb-secret-token" not in rendered
    assert report["bot_token"]["present"] is True
    assert report["bot_token"]["fingerprint"]


def test_slack_notification_readiness_reports_selected_route_and_sample() -> None:
    report = slack_notification_readiness(settings=_ready_settings(), route="hot_leads", render_sample=True)

    assert report["configured"] is True
    assert report["would_post"] is True
    assert report["selected_route"] == "hot_leads"
    assert report["routes"]["hot_leads"]["configured"] is True
    assert report["routes"]["hot_leads"]["channel_id"]["present"] is True
    assert report["routes"]["hot_leads"]["channel_id"]["shape"]["valid_prefix"] is True
    assert report["sample"]["route"] == "hot_leads"
    assert "token" not in json.dumps(report["sample"]).lower()


def test_slack_notification_readiness_blocks_invalid_channel_shape() -> None:
    report = slack_notification_readiness(
        settings=_ready_settings(slack_channel_hot_leads="not-a-channel"),
        route="hot_leads",
    )

    assert report["configured"] is False
    assert report["would_post"] is False
    assert report["routes"]["hot_leads"]["configured"] is False
    assert report["routes"]["hot_leads"]["channel_id"]["shape"]["looks_like_channel_id"] is False
    assert "SLACK_CHANNEL_HOT_LEADS must be a Slack channel ID" in report["missing"]


def test_slack_notification_readiness_keeps_legacy_fallbacks_visible_but_prefers_route_vars() -> None:
    report = slack_notification_readiness(
        settings=_ready_settings(slack_channel_lead_runs=None, slack_channel_lease_option_inbound=None),
        render_sample=False,
    )

    assert report["configured"] is False
    assert "SLACK_CHANNEL_LEAD_RUNS" in report["missing"]
    assert "SLACK_CHANNEL_LEASE_OPTION_INBOUND" in report["missing"]
    assert report["routes"]["lead_runs"]["fallback_env_vars"] == ["SLACK_CHANNEL_LEADS"]
    assert report["routes"]["lease_option_inbound"]["fallback_env_vars"] == ["SLACK_CHANNEL_INTAKE"]
    assert report["legacy_channels"]["SLACK_CHANNEL_LEADS"]["preferred"] is False


def test_slack_notification_readiness_cli_loads_env_file_without_leaking_token(tmp_path, capsys) -> None:
    env_file = tmp_path / "slack.env"
    env_file.write_text(
        "\n".join(
            [
                "SLACK_NOTIFICATIONS_ENABLED=true",
                "SLACK_BOT_TOKEN=xoxb-secret-token",
                "SLACK_CHANNEL_HOT_LEADS=C123HOTLEADS",
            ]
        )
    )

    code = main(["--json", "--route", "hot_leads", "--render-sample", "--env-file", str(env_file)])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["would_post"] is True
    assert output["sample"]["route"] == "hot_leads"
    assert "xoxb-secret-token" not in json.dumps(output)


def test_slack_notification_readiness_env_file_ignores_ambient_slack_channel(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SLACK_CHANNEL_HOT_LEADS", "C123AMBIENT")
    env_file = tmp_path / "slack.env"
    env_file.write_text(
        "\n".join(
            [
                "SLACK_NOTIFICATIONS_ENABLED=true",
                "SLACK_BOT_TOKEN=xoxb-secret-token",
            ]
        )
    )

    code = main(["--json", "--route", "hot_leads", "--env-file", str(env_file)])

    assert code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["configured"] is False
    assert output["would_post"] is False
    assert output["routes"]["hot_leads"]["channel_id"]["present"] is False
    assert "SLACK_CHANNEL_HOT_LEADS" in output["missing"]
