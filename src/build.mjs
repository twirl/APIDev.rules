import { readFileSync, writeFileSync } from "node:fs";

const SOURCE_FILES = {
    api_developer_role: "src/roles/API developer.md",
    spec_reviewer_role: "src/roles/Spec Reviewer.md",
    api_development_framework: "src/api-development-framework.md",
    backward_compatibility: "src/backward-compatibility.md",
    dos_and_donts: "src/dos-and-donts.md",
    rest_api: "src/rest-api.md",
    sdk: "src/sdk.md",
    ui_components: "src/ui-components.md",
};

const data = Object.fromEntries(
    Object.entries(SOURCE_FILES).map(([key, file]) => [
        key,
        readFileSync(file, "utf-8"),
    ]),
);

writeAgentsMd();

function writeAgentsMd() {
    writeFileSync(
        "./dist/AGENTS.md",
        [
            data["api_developer_role"],
            data["api_development_framework"],
            data["backward_compatibility"],
            data["rest_api"],
            data["sdk"],
            data["ui_components"],
            data["dos_and_donts"],
        ].join("\n"),
    );
}
