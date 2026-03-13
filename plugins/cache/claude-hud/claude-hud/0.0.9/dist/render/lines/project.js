import { getModelName, getProviderLabel } from '../../stdin.js';
import { cyan, dim, magenta, yellow, red } from '../colors.js';
export function renderProjectLine(ctx) {
    const display = ctx.config?.display;
    const parts = [];
    // 提升到函数顶部：终端宽度和显示宽度计算（ANSI-free）
    const termWidth = process.stdout?.columns
        || process.stderr?.columns
        || (Number.parseInt(process.env.COLUMNS ?? '', 10) || 0)
        || 80;
    const getDisplayWidth = (s) => [...s].reduce((w, c) => w + ((c.codePointAt(0) ?? 0) > 0x2E7F ? 2 : 1), 0);
    // 通用截断：逐字符 + '…'（path 和 branch 共用）
    const truncateStr = (s, maxW) => {
        if (getDisplayWidth(s) <= maxW)
            return s;
        let width = 0;
        let cutIdx = 0;
        for (const c of s) {
            const cw = (c.codePointAt(0) ?? 0) > 0x2E7F ? 2 : 1;
            if (width + cw > maxW - 1)
                break;
            width += cw;
            cutIdx += c.length;
        }
        return s.slice(0, cutIdx) + '…';
    };
    // --- Model badge ---
    let modelVisibleWidth = 0;
    if (display?.showModel !== false) {
        const model = getModelName(ctx.stdin);
        const providerLabel = getProviderLabel(ctx.stdin);
        const showUsage = display?.showUsage !== false;
        const planName = showUsage ? ctx.usageData?.planName : undefined;
        const hasApiKey = !!process.env.ANTHROPIC_API_KEY;
        const billingLabel = showUsage ? (planName ?? (hasApiKey ? red('API') : undefined)) : undefined;
        const planDisplay = providerLabel ?? billingLabel;
        const modelDisplay = planDisplay ? `${model} | ${planDisplay}` : model;
        parts.push(cyan(`[${modelDisplay}]`));
        modelVisibleWidth = getDisplayWidth(`[${modelDisplay}]`);
    }
    // --- 预提取 git 原始数据（用��宽度预计算）---
    const gitConfig = ctx.config?.gitStatus;
    const showGit = gitConfig?.enabled ?? true;
    let branchRaw = '';
    let isDirty = false;
    let gitExtraStr = ''; // ahead/behind/fileStats 拼接后的纯文本
    if (showGit && ctx.gitStatus) {
        branchRaw = ctx.gitStatus.branch;
        isDirty = (gitConfig?.showDirty ?? true) && ctx.gitStatus.isDirty;
        const extraParts = [];
        if (gitConfig?.showAheadBehind) {
            if (ctx.gitStatus.ahead > 0)
                extraParts.push(` ↑${ctx.gitStatus.ahead}`);
            if (ctx.gitStatus.behind > 0)
                extraParts.push(` ↓${ctx.gitStatus.behind}`);
        }
        if (gitConfig?.showFileStats && ctx.gitStatus.fileStats) {
            const { modified, added, deleted, untracked } = ctx.gitStatus.fileStats;
            const statParts = [];
            if (modified > 0)
                statParts.push(`!${modified}`);
            if (added > 0)
                statParts.push(`+${added}`);
            if (deleted > 0)
                statParts.push(`✘${deleted}`);
            if (untracked > 0)
                statParts.push(`?${untracked}`);
            if (statParts.length > 0)
                extraParts.push(` ${statParts.join(' ')}`);
        }
        gitExtraStr = extraParts.join('');
    }
    // --- 预提取 project path 原始字符串 ---
    const cwd = ctx.stdin.cwd;
    const hasProject = display?.showProject !== false && !!cwd;
    let projectPath = '';
    if (hasProject) {
        const segments = cwd.split(/[/\\]/).filter(Boolean);
        const pathLevels = ctx.config?.pathLevels ?? 1;
        projectPath = segments.length > 0 ? segments.slice(-pathLevels).join('/') : '/';
    }
    const hasGit = showGit && !!ctx.gitStatus && branchRaw.length > 0;
    // --- 动态宽度分配（取代硬编码 termWidth - 45）---
    const configMaxPath = ctx.config?.maxPathWidth;
    let maxPathWidth = Math.max(10, termWidth - 45); // 兜底值
    let maxBranchWidth = 20; // 兜底值
    if (hasProject || hasGit) {
        const hasSep = parts.length > 0;
        const sepWidth = hasSep ? 3 : 0; // ' │ '
        const gitFrameWidth = hasGit ? 6 : 0; // 'git:(' + ')'
        const dirtyWidth = (hasGit && isDirty) ? 1 : 0;
        const gitExtraWidth = getDisplayWidth(gitExtraStr);
        const pathGitGapWidth = (hasProject && hasGit) ? 1 : 0; // path 和 git:( 之间的空格
        const sessionNameWidth = (display?.showSessionName && ctx.transcript.sessionName)
            ? getDisplayWidth(` \u2502 ${ctx.transcript.sessionName}`)
            : 0;
        const totalOverhead = sepWidth + gitFrameWidth + dirtyWidth + gitExtraWidth + pathGitGapWidth + sessionNameWidth;
        const available = Math.max(0, termWidth - modelVisibleWidth - totalOverhead);
        const pathFullWidth = hasProject ? getDisplayWidth(projectPath) : 0;
        const branchFullWidth = hasGit ? getDisplayWidth(branchRaw) : 0;
        if (typeof configMaxPath === 'number') {
            // 用户手动指定 maxPathWidth，branch 拿剩余
            maxPathWidth = configMaxPath;
            maxBranchWidth = Math.max(12, available - configMaxPath);
        }
        else if (pathFullWidth + branchFullWidth <= available) {
            // 两者都放得下，不截断
            maxPathWidth = pathFullWidth;
            maxBranchWidth = branchFullWidth;
        }
        else {
            // 需要截断：branch 优先拿 20，path 最低 10
            const branchAlloc = Math.min(branchFullWidth, 20);
            const pathAlloc = Math.max(10, available - branchAlloc);
            maxBranchWidth = Math.max(12, available - pathAlloc);
            maxPathWidth = pathAlloc;
        }
    }
    // --- 渲染 project path ---
    let projectPart = null;
    if (hasProject) {
        const effectiveMaxPath = typeof configMaxPath === 'number' ? configMaxPath : maxPathWidth;
        projectPart = yellow(truncateStr(projectPath, effectiveMaxPath));
    }
    // --- 渲染 git 部分（含分支截断）---
    let gitPart = '';
    if (hasGit) {
        const displayBranch = truncateStr(branchRaw, maxBranchWidth);
        const gitParts = [displayBranch];
        if (isDirty)
            gitParts.push('*');
        if (gitExtraStr)
            gitParts.push(gitExtraStr);
        gitPart = `${magenta('git:(')}${cyan(gitParts.join(''))}${magenta(')')}`;
    }
    if (projectPart && gitPart) {
        parts.push(`${projectPart} ${gitPart}`);
    }
    else if (projectPart) {
        parts.push(projectPart);
    }
    else if (gitPart) {
        parts.push(gitPart);
    }
    if (display?.showSessionName && ctx.transcript.sessionName) {
        parts.push(dim(ctx.transcript.sessionName));
    }
    if (parts.length === 0) {
        return null;
    }
    return parts.join(' \u2502 ');
}
//# sourceMappingURL=project.js.map