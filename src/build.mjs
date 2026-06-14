import {
    copyFile,
    mkdir,
    readFile,
    rm,
    writeFile,
    access,
    constants,
} from "node:fs/promises";
import { createWriteStream } from "node:fs";
import { join } from "node:path";
import archiver from "archiver";

const SOURCE_PATHS = {
    api_developer_role: "src/roles/API developer.md",
    spec_reviewer_role: "src/roles/Spec Reviewer.md",
    api_developer_skill: "src/skills/API Developer.md",
    api_review_skill: "src/skills/API Review.md",
    api_development_framework: "src/api-development-framework.md",
    api_review_framework: "src/api-review-framework.md",
    backward_compatibility: "src/backward-compatibility.md",
    dos_and_donts: "src/dos-and-donts.md",
    rest_api: "src/rest-api.md",
    sdk: "src/sdk.md",
    ui_components: "src/ui-components.md",
};

async function main() {
    await ensureDirExists("./dist");
    const sourceFiles = await readAllSourceFiles();
    await writeAgentsMd(sourceFiles);
    await writeApiDevelopmentSkill(sourceFiles);
    await writeApiReviewSkill(sourceFiles);
}

main()
    .catch((e) => console.error(e))
    .finally(() => process.exit(0));

async function writeAgentsMd(sourceFiles) {
    await writeFile(
        "./dist/AGENTS.md",
        [
            sourceFiles.api_developer_role,
            sourceFiles.api_development_framework,
            sourceFiles.backward_compatibility,
            sourceFiles.rest_api,
            sourceFiles.sdk,
            sourceFiles.ui_components,
            sourceFiles.dos_and_donts,
        ].join("\n"),
        "utf-8",
    );
}

async function writeApiDevelopmentSkill(SOURCE_FILES) {
    const skillDir = "./dist/skills/api-development";
    const referencesDir = join(skillDir, "references");

    await rm(skillDir, { recursive: true, force: true });
    await ensureDirExists(referencesDir);

    await writeFile(
        join(skillDir, "SKILL.md"),
        SOURCE_FILES.api_developer_skill,
        "utf-8",
    );

    const refFiles = [
        "api-development-framework.md",
        "backward-compatibility.md",
        "dos-and-donts.md",
        "rest-api.md",
        "sdk.md",
        "ui-components.md",
    ];
    for (const file of refFiles) {
        await copyFile(join("src", file), join(referencesDir, file));
    }

    await createApiDevelopmentZip(skillDir);
}

async function writeApiReviewSkill(SOURCE_FILES) {
    const skillDir = "./dist/skills/api-review";
    const referencesDir = join(skillDir, "references");

    await rm(skillDir, { recursive: true, force: true });
    await ensureDirExists(referencesDir);

    await writeFile(
        join(skillDir, "SKILL.md"),
        SOURCE_FILES.api_review_skill,
        "utf-8",
    );

    const refFiles = [
        "api-review-framework.md",
        "dos-and-donts.md",
        "rest-api.md",
        "sdk.md",
        "ui-components.md",
    ];
    for (const file of refFiles) {
        await copyFile(join("src", file), join(referencesDir, file));
    }

    await createSkillZip(skillDir, "api-review");
}

async function createApiDevelopmentZip(skillDir) {
    await createSkillZip(skillDir, "api-development");
}

async function createSkillZip(skillDir, skillName) {
    const zipPath = join("./dist/skills", `${skillName}.zip`);
    const output = createWriteStream(zipPath);
    const archiver = (await import("archiver")).default;
    const archive = archiver("zip", { zlib: { level: 9 } });
    return new Promise((resolve, reject) => {
        output.on("close", resolve);
        archive.on("error", reject);
        archive.pipe(output);
        archive.directory(skillDir, skillName);
        archive.finalize();
    });
}

async function ensureDirExists(dirPath) {
    try {
        await access(dirPath, constants.F_OK);
    } catch {
        await mkdir(dirPath, { recursive: true });
    }
}

async function readAllSourceFiles() {
    const entries = Object.entries(SOURCE_PATHS);
    const out = {};
    for (const [key, path] of entries) {
        out[key] = await readFile(path, "utf-8");
    }
    return out;
}
