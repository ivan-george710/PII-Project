/* Synthetic component demonstrations. The film owns the clock. */
(function () {
  'use strict';

  const instances = new Map();
  const clamp = value => Math.max(0, Math.min(1, value));
  const span = (value, from, to) => clamp((value - from) / (to - from));
  const ease = value => 1 - Math.pow(1 - clamp(value), 4);
  const face = 'assets/face.png';
  const chart = (x, y, width = 230, height = 70) => `<svg x="${x}" y="${y}" width="${width}" height="${height}" viewBox="0 0 230 70" class="cd-chart"><path class="cd-chart-grid" d="M0 10H230M0 36H230M0 63H230"/><path class="cd-chart-line" d="M3 58 32 50 60 54 91 31 126 38 161 17 191 24 226 5"/></svg>`;
  const arrow = (x, y, size = 20) => `<svg x="${x}" y="${y}" width="${size}" height="${size}" viewBox="0 0 24 24" class="cd-line-icon"><path d="M4 12h15m-6-6 6 6-6 6"/></svg>`;
  const download = `<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>`;
  const lock = `<path d="M6 11h12v10H6zm3 0V7a3 3 0 0 1 6 0"/>`;
  const paper = (x, y, w, h) => `<path class="cd-paper" d="M${x} ${y}h${w - 20}l20 20v${h - 20}H${x}z"/><path class="cd-fold" d="M${x + w - 20} ${y}v20h20"/>`;
  const label = (x, y, value, extra = '') => `<text x="${x}" y="${y}" ${extra}>${value}</text>`;
  const route = (className, path) => `<path class="cd-route ${className}" pathLength="1" d="${path}"/>`;
  const svg = (viewBox, body, aria) => `<svg class="cd-visual" viewBox="${viewBox}" role="img" aria-label="${aria}">${body}</svg>`;
  const mask = (x, y, w, text, className) => `<g class="cd-mask ${className}" style="--mask-width:${w}px"><rect x="${x}" y="${y}" width="${w}" height="25" rx="1"/><text x="${x + 7}" y="${y + 17}">${text}</text></g>`;

  const templates = {
    source: () => svg('0 0 390 455', `
      <path class="cd-chat-rail" d="M0 385H390"/>
      <g class="cd-source-attaching">${paper(5, 296, 60, 75)}<path class="cd-fold" d="M17 320h30m-30 10h23m-23 10h28"/>${label(17, 359, 'PDF', 'class="cd-small cd-ink"')}</g>
      <g class="cd-composer"><rect x="0" y="385" width="390" height="57" rx="15"/>
        <path class="cd-line-icon" d="M23 405v17m-8-8h17"/>
        ${label(44, 420, 'Attach a document', 'class="cd-composer-placeholder"')}
        <g class="cd-composer-file"><rect x="43" y="397" width="267" height="33" rx="6"/>${label(57, 419, 'quarterly-report.pdf')}</g>
        <g class="cd-send-icon"><circle cx="359" cy="413" r="16"/><path d="M359 420v-14m-6 6 6-6 6 6"/></g>
      </g>
      <g class="cd-source-sent"><rect x="159" y="14" width="231" height="109" rx="13"/>
        ${label(179, 42, 'quarterly-report.pdf', 'class="cd-medium"')}
        <path class="cd-file-lines" d="M180 62h185m-185 14h135m-135 14h155"/>
        ${label(179, 109, 'Sent · original', 'class="cd-small"')}
      </g>
      <g class="cd-source-returned"><rect class="cd-return-surface" x="0" y="157" width="310" height="195" rx="13"/>
        ${label(20, 187, 'Redacted copy', 'class="cd-medium"')}
        <rect class="cd-dark-mask" x="20" y="204" width="113" height="24" rx="1"/>${label(26, 221, '[PERSON]', 'class="cd-mask-copy"')}
        ${chart(20, 246, 250, 61)}
        ${label(20, 330, 'Download available', 'class="cd-small"')}
        <svg x="270" y="313" width="22" height="22" viewBox="0 0 24 24" class="cd-line-icon">${download}</svg>
      </g>
    `, 'A synthetic PDF attaches to the composer, is sent, and returns as a redacted downloadable copy with its chart preserved.'),

    extract: () => svg('0 0 440 450', `
      <path class="cd-source-spine" d="M21 17V355"/>
      <g class="cd-extract-layer cd-native">${paper(31, 14, 186, 92)}
        ${label(45, 38, 'Native text', 'class="cd-small cd-ink"')}${label(45, 62, 'Dana Ellis', 'class="cd-ink"')}
        <path class="cd-region-box cd-native-region" d="M43 45h98v24H43z"/>
        <path class="cd-paper-lines" d="M45 82h146"/>
      </g>
      <g class="cd-extract-layer cd-scanned">${paper(31, 133, 186, 92)}
        ${label(45, 157, 'Scanned page', 'class="cd-small cd-ink"')}${label(45, 181, 'demo_123', 'class="cd-ink"')}
        <path class="cd-region-box cd-ocr-region" d="M43 164h105v24H43z"/>
        <path class="cd-paper-lines" d="M45 201h122"/>
        <path class="cd-ocr-beam" d="M32 150H216"/>
      </g>
      <g class="cd-extract-layer cd-embedded">${paper(31, 252, 186, 105)}
        ${label(45, 276, 'Embedded image', 'class="cd-small cd-ink"')}
        <rect class="cd-screen" x="44" y="289" width="159" height="45"/>
        ${label(52, 317, 'EMP-2048', 'class="cd-ink"')}
        <path class="cd-region-box cd-image-region" d="M50 297h107v25H50z"/>
      </g>
      ${route('cd-extract-route cd-extract-route-a', 'M217 58H235Q251 58 251 68H272')}
      ${route('cd-extract-route cd-extract-route-b', 'M217 177H237Q251 177 251 183H272')}
      ${route('cd-extract-route cd-extract-route-c', 'M217 306H236Q251 306 251 300H272')}
      <path class="cd-ledger-line" d="M275 28V351"/>
      <g class="cd-map-entry cd-map-a">${label(287, 52, 'Dana Ellis')}${label(287, 76, 'p1 · native', 'class="cd-small"')}${label(287, 96, 'x38 · y54', 'class="cd-small"')}<circle cx="275" cy="57" r="4"/></g>
      <g class="cd-map-entry cd-map-b">${label(287, 171, 'demo_123')}${label(287, 195, 'p2 · OCR', 'class="cd-small"')}${label(287, 215, 'x42 · y76', 'class="cd-small"')}<circle cx="275" cy="176" r="4"/></g>
      <g class="cd-map-entry cd-map-c">${label(287, 292, 'EMP-2048')}${label(287, 316, 'p2 · image 1', 'class="cd-small"')}${label(287, 336, 'x12 · y20', 'class="cd-small"')}<circle cx="275" cy="297" r="4"/></g>
      <path class="cd-foot-rule" d="M31 390H409"/>
      ${label(31, 418, 'Text + source coordinates', 'class="cd-footer-copy"')}
      <g class="cd-map-stamp"><path d="m372 412 9 9 19-21"/></g>
    `, 'Native text, scanned text, and an embedded image become text records with their page and region coordinates.'),

    detect: () => svg('0 0 440 450', `
      ${paper(0, 17, 205, 373)}
      ${label(15, 44, 'Source regions', 'class="cd-small cd-ink"')}
      ${label(15, 83, 'Dana Ellis', 'class="cd-ink"')}${label(15, 125, 'dana@example.test', 'class="cd-ink cd-small"')}
      ${label(15, 167, 'EMP-2048', 'class="cd-ink"')}${label(15, 209, 'demo_123', 'class="cd-ink"')}
      <image href="${face}" x="16" y="234" width="90" height="137" preserveAspectRatio="xMidYMin slice" class="cd-portrait"/>
      <g class="cd-detection-boxes">
        <rect class="cd-entity-box cd-entity-a" x="10" y="64" width="107" height="26"/>
        <rect class="cd-entity-box cd-entity-b" x="10" y="107" width="176" height="25"/>
        <rect class="cd-entity-box cd-entity-c" x="10" y="148" width="115" height="26"/>
        <rect class="cd-entity-box cd-entity-d" x="10" y="190" width="116" height="26"/>
        <rect class="cd-entity-box cd-entity-e" x="38" y="245" width="47" height="67"/>
      </g>
      ${route('cd-detect-route cd-detect-a', 'M117 77H224Q237 77 237 72H264')}
      ${route('cd-detect-route cd-detect-b', 'M186 120H229Q241 120 241 130H264')}
      ${route('cd-detect-route cd-detect-c', 'M125 161H228Q242 161 242 188H264')}
      ${route('cd-detect-route cd-detect-d', 'M126 203H222Q241 203 241 246H264')}
      ${route('cd-detect-route cd-detect-e', 'M85 278H229Q241 278 241 318H264')}
      <g class="cd-classified cd-class-a"><circle cx="264" cy="72" r="4"/>${label(276, 78, 'PERSON')}</g>
      <g class="cd-classified cd-class-b"><circle cx="264" cy="130" r="4"/>${label(276, 136, 'EMAIL')}</g>
      <g class="cd-classified cd-class-c"><circle cx="264" cy="188" r="4"/>${label(276, 184, 'EMPLOYEE')}${label(276, 204, 'ID', 'class="cd-small"')}</g>
      <g class="cd-classified cd-class-d"><circle cx="264" cy="246" r="4"/>${label(276, 252, 'PASSWORD')}</g>
      <g class="cd-classified cd-class-e"><circle cx="264" cy="318" r="4"/>${label(276, 324, 'FACE')}</g>
      ${label(0, 422, 'Finding → original region', 'class="cd-footer-copy"')}
    `, 'The same synthetic name, email, employee ID, password, and public test portrait are classified while keeping their source boxes.'),

    rules: () => svg('0 0 440 155', `
      <path class="cd-rules-divider" d="M0 76H440"/>
      <g class="cd-rule-exact">
        ${label(0, 17, 'Exact', 'class="cd-small"')}${label(0, 44, 'Orion', 'class="cd-rule-pattern"')}
        ${label(145, 17, 'Value', 'class="cd-small"')}${label(145, 44, 'Orion')}
        <path class="cd-rule-bracket cd-exact-bracket" d="M139 25v26h59V25"/>
        <path class="cd-rule-scan cd-exact-scan" d="M142 25V51"/>
        ${arrow(219, 27, 21)}
        <g class="cd-rule-replacement cd-exact-replacement"><rect x="260" y="23" width="180" height="30" rx="2"/>${label(270, 44, '[CUSTOM]')}</g>
      </g>
      <g class="cd-rule-regex">
        ${label(0, 103, 'Regex', 'class="cd-small"')}${label(0, 130, 'EMP-[0-9]{4}', 'class="cd-rule-pattern"')}
        ${label(145, 103, 'Value', 'class="cd-small"')}${label(145, 130, 'EMP-2048')}
        <path class="cd-rule-bracket cd-regex-bracket" d="M139 111v26h102v-26"/>
        <path class="cd-rule-scan cd-regex-scan" d="M142 111V137"/>
        ${arrow(245, 113, 21)}
        <g class="cd-rule-replacement cd-regex-replacement"><rect x="280" y="109" width="160" height="30" rx="2"/>${label(290, 130, '[EMPLOYEE ID]')}</g>
      </g>
    `, 'An exact rule matches Orion and a regular expression matches EMP-2048; the matched values become their configured replacements.'),

    redact: () => svg('0 0 440 450', `
      ${paper(34, 0, 372, 421)}
      ${label(57, 35, 'Quarterly report', 'class="cd-small cd-ink"')}
      <path class="cd-paper-lines" d="M57 49H382"/>
      ${label(57, 77, 'Dana Ellis', 'class="cd-ink"')}${label(57, 111, 'dana@example.test', 'class="cd-ink"')}
      ${label(57, 145, 'EMP-2048', 'class="cd-ink"')}${label(57, 179, 'Project Orion', 'class="cd-ink"')}
      ${mask(54, 58, 124, '[PERSON]', 'cd-redact-name')}
      ${mask(54, 92, 199, '[EMAIL]', 'cd-redact-email')}
      ${mask(54, 126, 157, '[EMPLOYEE ID]', 'cd-redact-id')}
      ${mask(119, 160, 124, '[CUSTOM]', 'cd-redact-custom')}
      ${label(57, 217, 'Business results', 'class="cd-small cd-ink"')}
      ${chart(57, 236, 216, 100)}
      <image href="${face}" x="290" y="215" width="90" height="124" preserveAspectRatio="xMidYMin slice" class="cd-portrait"/>
      <g class="cd-face-mask"><rect x="310" y="223" width="51" height="69" fill="#151515"/><path d="M310 235h51m-51 14h51m-51 14h51m-51 14h51M323 223v69m13-69v69m13-69v69"/></g>
      <g class="cd-chart-retained"><path class="cd-ink-line" d="m58 364 8 8 16-18"/>${label(93, 369, 'Chart retained', 'class="cd-small cd-ink"')}</g>
      ${label(57, 402, 'Synthetic returned artifact', 'class="cd-small cd-ink"')}
    `, 'Sensitive text is replaced and the face region is masked in a synthetic saved copy; the business chart stays intact.'),

    verify: () => svg('0 0 440 310', `
      ${paper(18, 4, 268, 207)}
      ${label(35, 33, 'Saved copy · reopen', 'class="cd-small cd-ink"')}
      <rect class="cd-dark-mask" x="35" y="51" width="122" height="20"/>
      <path class="cd-paper-lines" d="M35 85h221m-221 18h183"/>
      ${label(35, 136, 'demo_123', 'class="cd-ink"')}
      <g class="cd-remnant-box"><rect x="29" y="117" width="113" height="26"/><path d="M142 130H304"/></g>
      <g class="cd-verify-repair"><rect x="30" y="116" width="115" height="29"/><text x="38" y="136">[PASSWORD]</text></g>
      ${chart(35, 157, 200, 33)}
      <path class="cd-verify-beam" d="M19 41H284"/>
      <g class="cd-verify-finding">${label(310, 126, 'Known', 'class="cd-small"')}${label(310, 147, 'remnant', 'class="cd-small"')}</g>
      <g class="cd-verify-check"><circle cx="337" cy="89" r="28"/><path pathLength="1" d="m324 90 9 9 19-21"/></g>
      <g class="cd-checkpoints"><path class="cd-checkpoint-rail" d="M35 254H405"/>
        <circle class="cd-check-a" cx="35" cy="254" r="5"/><circle class="cd-check-b" cx="155" cy="254" r="5"/>
        <circle class="cd-check-c" cx="279" cy="254" r="5"/><circle class="cd-check-d" cx="405" cy="254" r="5"/>
        ${label(13, 280, 'Reopen', 'class="cd-small"')}${label(124, 280, 'Remnant', 'class="cd-small"')}${label(256, 280, 'Repair', 'class="cd-small"')}${label(375, 280, 'Recheck', 'class="cd-small"')}
      </g>
    `, 'A saved artifact is reopened, a known password remnant is found, its region is repaired, and the saved copy is checked again.'),

    audit: () => svg('0 0 440 310', `
      ${paper(0, 16, 144, 172)}
      ${label(13, 42, 'Page 1', 'class="cd-small cd-ink"')}
      <path class="cd-paper-lines" d="M13 61h115m-115 58h111m-111 18h91m-91 18h103"/>
      <g class="cd-audit-crop"><rect x="9" y="75" width="112" height="30"/><text class="cd-ink" x="15" y="96">Dana Ellis</text></g>
      <path class="cd-source-crosshair" d="M5 72v-7h7m112 0h7v7M5 109v7h7m112 0h7v-7"/>
      ${route('cd-audit-route cd-audit-source', 'M121 90H158Q172 90 172 46H194')}
      ${route('cd-audit-route cd-audit-replacement', 'M254 75V113')}
      ${route('cd-audit-route cd-audit-revision', 'M254 173V211')}
      <g class="cd-lineage cd-lineage-a"><path d="M194 15H440V75H194"/>${label(210, 37, 'Finding D000001', 'class="cd-small"')}${label(210, 60, 'PERSON')}</g>
      <g class="cd-lineage cd-lineage-b"><path d="M194 113H440V173H194"/>${label(210, 135, 'Replacement', 'class="cd-small"')}${label(210, 158, '[PERSON_001]')}</g>
      <g class="cd-lineage cd-lineage-c"><path d="M194 211H440V276H194"/>${label(210, 235, 'Revision 0', 'class="cd-small"')}${label(210, 259, 'Artifact A1')}</g>
      <path class="cd-audit-binding" pathLength="1" d="M10 190V245Q10 259 24 259H194"/>
      ${label(0, 299, 'Source → finding → exact copy', 'class="cd-footer-copy"')}
    `, 'A cropped source region joins a stable finding, its replacement, and the revision-bound returned artifact.'),

    manager: () => svg('0 0 450 505', `
      <g class="cd-manager-report"><path class="cd-manager-row-rule" d="M0 56H450"/>
        ${label(0, 24, 'quarterly-report.pdf', 'class="cd-medium"')}${label(450, 24, 'Just now', 'class="cd-small" text-anchor="end"')}
        ${label(0, 47, 'Affected evidence · revision 0', 'class="cd-small"')}
      </g>
      <g class="cd-manager-receipt"><rect x="77" y="79" width="296" height="111" rx="3"/>${label(93, 105, 'Affected portion', 'class="cd-small"')}${label(93, 144, 'Dana Ellis')}${label(93, 171, 'p1 · region 3', 'class="cd-small"')}</g>
      <g class="cd-manager-comparison">
        <path class="cd-manager-compare-divider" d="M224 98V271"/>
        <g class="cd-manager-original">${label(0, 105, 'Original part', 'class="cd-small"')}${label(0, 143, 'Dana Ellis')}
          <svg x="0" y="165" width="112" height="101" viewBox="157 25 155 170" preserveAspectRatio="xMidYMid slice" overflow="hidden"><image href="${face}" width="512" height="512" class="cd-portrait"/></svg>
          <path class="cd-crop-corners" d="M-1 174v-10h10m94 0h10v10M-1 257v10h10m94 0h10v-10"/>
        </g>
        <g class="cd-manager-redacted">${label(249, 105, 'Redacted part', 'class="cd-small"')}
          <rect class="cd-dark-mask" x="249" y="124" width="191" height="27"/>${label(256, 144, '[PERSON_001]', 'class="cd-mask-copy"')}
          <rect class="cd-dark-mask" x="249" y="165" width="112" height="101"/>${label(305, 221, '[FACE]', 'class="cd-mask-copy" text-anchor="middle"')}
        </g>
      </g>
      <g class="cd-manager-controls"><g class="cd-manager-approve"><rect x="0" y="298" width="146" height="47" rx="9"/>${label(73, 328, 'Approve', 'text-anchor="middle"')}</g><g class="cd-manager-deny"><rect x="159" y="298" width="146" height="47" rx="9"/>${label(232, 328, 'Deny', 'text-anchor="middle"')}</g></g>
      <path class="cd-manager-artifact-rule" d="M0 372H450"/>
      <g class="cd-manager-artifact"><svg x="0" y="398" width="27" height="27" viewBox="0 0 24 24" class="cd-line-icon cd-manager-download">${download}</svg><svg x="0" y="398" width="27" height="27" viewBox="0 0 24 24" class="cd-line-icon cd-manager-lock">${lock}</svg>${label(43, 420, 'Artifact A1', 'class="cd-medium"')}<text class="cd-manager-status" x="43" y="447">Pending · download available</text></g>
      <g class="cd-manager-outage">${label(43, 479, 'Service outage · download available', 'class="cd-small"')}</g>
    `, 'The manager receives only an affected snippet and crop, automatically opens the comparison, and shows pending, approved, and denied artifact availability. Pending and outage downloads stay available.'),

    network: () => svg('0 0 670 350', `
      ${label(0, 27, 'Employee upload', 'class="cd-small"')}${label(494, 27, 'Destination', 'class="cd-small"')}
      ${paper(0, 49, 167, 172)}${label(13, 78, 'Quarterly summary', 'class="cd-small cd-ink"')}${label(13, 112, 'Dana Ellis', 'class="cd-ink"')}${label(13, 141, 'EMP-2048', 'class="cd-ink"')}${chart(13, 161, 137, 38)}
      <path class="cd-network-rail" d="M167 134H494"/>
      <g class="cd-managed-gateway"><rect x="264" y="55" width="142" height="166" rx="12"/>
        <svg x="304" y="79" width="62" height="62" viewBox="0 0 64 64" class="cd-gateway-mark"><rect x="16" y="16" width="32" height="32" rx="10" transform="rotate(45 32 32)"/></svg>
        ${label(335, 170, 'Managed', 'text-anchor="middle"')}${label(335, 193, 'gateway', 'text-anchor="middle"')}
        <path class="cd-gateway-shutter" d="M270 60V216"/>
      </g>
      <g class="cd-network-raw-packet"><rect x="0" y="0" width="74" height="44" rx="3"/>${label(37, 28, 'Dana Ellis', 'class="cd-small" text-anchor="middle"')}</g>
      <g class="cd-network-safe-packet"><rect x="0" y="0" width="80" height="44" rx="3"/>${label(40, 28, '[PERSON]', 'class="cd-small" text-anchor="middle"')}</g>
      <g class="cd-network-destination">${paper(494, 49, 176, 172)}${label(507, 78, 'Quarterly summary', 'class="cd-small cd-ink"')}<rect class="cd-dark-mask" x="507" y="95" width="116" height="25"/>${label(514, 112, '[PERSON]', 'class="cd-mask-copy"')}<rect class="cd-dark-mask" x="507" y="126" width="149" height="25"/>${label(514, 143, '[EMPLOYEE ID]', 'class="cd-mask-copy"')}${chart(507, 161, 148, 38)}</g>
      <g class="cd-network-clean"><path d="m315 252 10 10 22-23"/>${label(335, 295, 'Sanitise before destination', 'class="cd-footer-copy" text-anchor="middle"')}</g>
      ${label(0, 337, 'Future scope · managed HTTPS inspection', 'class="cd-small"')}
    `, 'A proposed managed HTTPS gateway sanitises an upload before the destination receives it; useful business content is preserved.'),

    shares: () => svg('0 0 670 350', `
      <path class="cd-share-conversation-rule" d="M0 0H409V268H0"/>
      <g class="cd-share-user"><rect x="90" y="19" width="300" height="72" rx="12"/>${label(108, 47, 'Send the quarterly summary', 'class="cd-small"')}${label(108, 74, 'dana@example.test')}
        ${mask(103, 54, 219, '[EMAIL]', 'cd-share-email')}
      </g>
      <g class="cd-share-reply"><rect x="0" y="111" width="320" height="139" rx="12"/>${label(17, 140, 'Q3 chart attached', 'class="cd-small"')}${chart(17, 165, 184, 54)}
        <image href="${face}" x="230" y="153" width="72" height="80" preserveAspectRatio="xMidYMin slice" class="cd-portrait"/>
        <g class="cd-share-face"><rect x="247" y="156" width="39" height="52"/><path d="M247 169h39m-39 13h39m-39 13h39"/></g>
      </g>
      <path class="cd-share-shutter" d="M1 1V267"/>
      ${route('cd-share-to-link', 'M410 134H468')}
      <g class="cd-share-link"><rect x="480" y="86" width="190" height="104" rx="11"/>
        <svg x="550" y="99" width="47" height="38" viewBox="0 0 48 38" class="cd-line-icon"><path d="m20 24-4 4a8 8 0 0 1-11-11l8-8a8 8 0 0 1 11 0m4 5 4-4a8 8 0 0 1 11 11l-8 8a8 8 0 0 1-11 0m-8-3 16-16"/></svg>
        ${label(575, 159, 'Redacted share', 'text-anchor="middle"')}${label(575, 181, 'Ready to publish', 'class="cd-small" text-anchor="middle"')}
      </g>
      ${label(0, 306, 'Protect sensitive parts before the link', 'class="cd-footer-copy"')}
      ${label(0, 337, 'Future scope · sharing integration', 'class="cd-small"')}
    `, 'A proposed sharing integration redacts the conversation email and face before creating a link, while retaining the conversation context and chart.'),
  };

  function put(instance, values) {
    for (const [name, value] of Object.entries(values)) {
      const text = typeof value === 'number' ? String(Math.round(value * 10000) / 10000) : value;
      if (instance.values[name] !== text) {
        instance.root.style.setProperty('--' + name, text);
        instance.values[name] = text;
      }
    }
  }

  function stage(instance, value, details = {}) {
    if (instance.element.dataset.demoState !== value) instance.element.dataset.demoState = value;
    instance.root.dataset.state = value;
    for (const [key, item] of Object.entries(details)) instance.element.dataset[key] = String(item);
  }

  function draw(instance, progress, moving) {
    const p = clamp(progress);
    const q = (a, b) => ease(span(p, a, b));
    const blur = (a, b, max = 2.1) => moving && p > a && p < b ? `${(Math.sin(span(p, a, b) * Math.PI) * max).toFixed(2)}px` : '0px';
    const values = {};
    let state;
    switch (instance.key) {
      case 'source': {
        const attach = q(.05, .20), sent = q(.30, .43), returned = q(.58, .73);
        Object.assign(values, {attach, sent, returned, 'attach-x': `${attach * 67}px`, 'attach-y': `${attach * 97}px`, 'attach-scale': 1 - attach * .52, 'attach-blur': blur(.05, .20), 'sent-y': `${(1 - sent) * 333}px`, 'sent-blur': blur(.30, .43), 'returned-y': `${(1 - returned) * 35}px`, 'returned-blur': blur(.58, .73)});
        state = p < .05 ? 'composer-empty' : p < .30 ? 'attached' : p < .58 ? 'sent' : 'returned';
        stage(instance, state, {download: p >= .58 ? 'available' : 'none', artifact: p >= .58 ? 'synthetic-redacted-copy' : 'original'});
        break;
      }
      case 'extract': {
        Object.assign(values, {'fan': q(.02, .19), 'fan-blur': blur(.02, .19), 'native-box': q(.16, .24), 'ocr-box': q(.34, .43), 'image-box': q(.51, .60), 'ocr-y': `${span(p, .25, .42) * 53}px`, 'ocr-visible': p > .25 && p < .43 ? 1 : 0, 'map-a': q(.21, .32), 'map-b': q(.43, .54), 'map-c': q(.60, .71), 'map-blur-a': blur(.21, .32), 'map-blur-b': blur(.43, .54), 'map-blur-c': blur(.60, .71), 'mapped': q(.72, .81)});
        state = p < .19 ? 'unfolding' : p < .34 ? 'native-mapped' : p < .51 ? 'ocr-mapped' : p < .71 ? 'image-mapped' : 'source-mapped';
        stage(instance, state, {sourceMap: p >= .71 ? 'complete' : 'assembling'});
        break;
      }
      case 'detect': {
        for (let i = 0; i < 5; i++) {
          const letter = 'abcde'[i], start = .05 + i * .135;
          values['detect-' + letter] = q(start, start + .11);
          values['detect-blur-' + letter] = blur(start, start + .11, 1.5);
        }
        state = p < .05 ? 'source-regions-ready' : p < .185 ? 'classifying-person' : p < .32 ? 'classifying-email' : p < .455 ? 'classifying-employee-id' : p < .59 ? 'classifying-password' : p < .70 ? 'classifying-face' : 'classified';
        stage(instance, state, {sourceBoxes: 'retained', classifiedEntities: p < .16 ? 0 : Math.min(5, Math.floor((p - .16) / .135) + 1)});
        break;
      }
      case 'rules': {
        Object.assign(values, {'exact-scan': `${span(p, .07, .23) * 53}px`, 'regex-scan': `${span(p, .40, .58) * 96}px`, 'exact-scanning': p > .07 && p < .23 ? 1 : 0, 'regex-scanning': p > .40 && p < .58 ? 1 : 0, 'exact-match': q(.22, .28), 'regex-match': q(.57, .64), 'exact-replaced': q(.30, .38), 'regex-replaced': q(.66, .75), 'exact-blur': blur(.30, .38, 1.2), 'regex-blur': blur(.66, .75, 1.2)});
        state = p < .22 ? 'scanning-exact' : p < .38 ? 'exact-matched' : p < .57 ? 'scanning-regex' : p < .75 ? 'regex-matched' : 'rules-applied';
        stage(instance, state, {exactRule: p >= .30 ? 'replaced' : p >= .22 ? 'matched' : 'scanning', regexRule: p >= .66 ? 'replaced' : p >= .57 ? 'matched' : 'scanning'});
        break;
      }
      case 'redact': {
        Object.assign(values, {'mask-name': q(.07, .17), 'mask-email': q(.20, .30), 'mask-id': q(.33, .43), 'mask-custom': q(.46, .56), 'mask-face': q(.61, .72), 'chart-retained': q(.76, .83), 'mask-blur': blur(.61, .72, 1.4)});
        state = p < .61 ? 'replacing-text' : p < .76 ? 'masking-face' : 'artifact-saved';
        stage(instance, state, {chart: 'preserved', textMask: p >= .56 ? 'complete' : 'forming', faceMask: p >= .72 ? 'complete' : 'forming'});
        break;
      }
      case 'verify': {
        const scanning = p < .40, rechecking = p > .66 && p < .83;
        Object.assign(values, {'verify-y': `${(scanning ? span(p, .05, .37) : span(p, .66, .83)) * 159}px`, 'verify-scanning': (p > .05 && p < .37) || rechecking ? 1 : 0, 'remnant': q(.37, .42) * (1 - q(.63, .70)), 'repair': q(.49, .61), 'verified': q(.83, .90), 'verify-reopen': q(0, .07), 'verify-remnant': q(.37, .42), 'verify-repaired': q(.59, .64), 'verify-rechecked': q(.83, .90), 'repair-blur': blur(.49, .61, 1.3)});
        state = p < .37 ? 'reopening-saved-artifact' : p < .49 ? 'known-remnant-found' : p < .66 ? 'repairing-saved-region' : p < .83 ? 'rechecking-saved-artifact' : 'known-remnant-cleared';
        stage(instance, state, {verificationScope: 'known-source-values', repair: p >= .61 ? 'saved' : p >= .49 ? 'in-progress' : 'none', universalPiiClaim: 'false'});
        break;
      }
      case 'audit': {
        Object.assign(values, {'audit-source': q(.05, .22), 'audit-finding': q(.22, .37), 'audit-replacement': q(.40, .55), 'audit-revision': q(.60, .75), 'audit-bind': q(.75, .84), 'lineage-blur-a': blur(.22, .37, 1.4), 'lineage-blur-b': blur(.40, .55, 1.4), 'lineage-blur-c': blur(.60, .75, 1.4)});
        state = p < .22 ? 'locating-source' : p < .40 ? 'finding-linked' : p < .60 ? 'replacement-linked' : p < .84 ? 'binding-revision' : 'lineage-complete';
        stage(instance, state, {finding: 'D000001', revision: '0', artifactBinding: p >= .75 ? 'A1' : 'assembling'});
        break;
      }
      case 'manager': {
        const report = q(.02, .12), open = q(.16, .28);
        const decision = p < .53 ? 'pending' : p < .74 ? 'approved' : 'denied';
        const denied = decision === 'denied', approved = decision === 'approved';
        Object.assign(values, {'manager-report': report, 'manager-open': open, 'manager-receipt': report * (1 - open), 'manager-open-x': `${(1 - open) * 60}px`, 'manager-report-blur': blur(.02, .12), 'manager-open-blur': blur(.16, .28), 'manager-approve': approved ? 1 : 0, 'manager-deny': denied ? 1 : 0, 'manager-blocked': denied ? 1 : 0, 'manager-outage': p >= .37 && p < .53 ? 1 : 0});
        state = p < .12 ? 'receiving-affected-evidence' : p < .28 ? 'opening-comparison' : decision;
        stage(instance, state, {decision, download: denied ? 'blocked' : 'available', reportScope: 'affected-only', comparison: p >= .28 ? 'open' : 'opening', revision: '0', managerService: p >= .37 && p < .53 ? 'outage' : 'online'});
        const status = denied ? 'Denied · download blocked' : approved ? 'Approved · download available' : 'Pending · download available';
        if (instance.status && instance.status.textContent !== status) instance.status.textContent = status;
        break;
      }
      case 'network': {
        const raw = q(.05, .29), safe = q(.49, .74);
        Object.assign(values, {'network-raw-x': `${158 + raw * 136}px`, 'network-safe-x': `${314 + safe * 187}px`, 'network-raw-visible': p >= .05 && p < .39 ? 1 : 0, 'network-safe-visible': p >= .49 && p < .79 ? 1 : 0, 'network-raw-blur': blur(.05, .29), 'network-safe-blur': blur(.49, .74), 'network-shutter-x': `${q(.31, .45) * 131}px`, 'network-shutter-visible': p >= .31 && p < .46 ? 1 : 0, 'network-destination': q(.75, .82), 'network-clean': q(.82, .89)});
        state = p < .31 ? 'upload-approaching-gateway' : p < .49 ? 'sanitising-payload' : p < .75 ? 'sanitised-payload-in-transit' : 'sanitised-payload-delivered';
        stage(instance, state, {implementation: 'future', destinationPayload: p >= .75 ? 'sanitised' : 'empty', sanitiseBeforeDestination: 'true'});
        break;
      }
      case 'shares': {
        Object.assign(values, {'share-email': q(.15, .32), 'share-face': q(.39, .54), 'share-shutter-x': `${q(.08, .57) * 407}px`, 'share-shutter-visible': p >= .08 && p < .57 ? 1 : 0, 'share-link': q(.67, .79), 'share-link-blur': blur(.67, .79), 'share-shutter-blur': blur(.08, .57, .6)});
        state = p < .32 ? 'redacting-conversation-text' : p < .54 ? 'redacting-conversation-image' : p < .67 ? 'share-content-protected' : 'redacted-link-created';
        stage(instance, state, {implementation: 'future', sensitiveParts: p >= .54 ? 'redacted' : 'processing', link: p >= .67 ? 'redacted-only' : 'not-created', chart: 'preserved'});
        break;
      }
    }
    put(instance, values);
    instance.element.dataset.demoProgress = p.toFixed(3);
    const transientMotion = Object.entries(values).some(([name, value]) => name.includes('blur') && parseFloat(value) > .001);
    instance.element.dataset.demoMoving = String(Boolean(moving && transientMotion));
  }

  function mount({nodes = {}} = {}) {
    for (const [key, make] of Object.entries(templates)) {
      const element = nodes[key];
      if (!element || typeof element.querySelector !== 'function') continue;
      if (instances.get(key)?.element === element) continue;
      const heading = element.querySelector('h2');
      const root = document.createElement('div');
      root.className = `cd-demo cd-${key}`;
      root.dataset.component = key;
      root.innerHTML = make();
      element.replaceChildren(...(heading ? [heading, root] : [root]));
      element.classList.add('component-demo');
      element.dataset.synthetic = 'true';
      const instance = {key, element, root, values: {}, status: root.querySelector('.cd-manager-status')};
      instances.set(key, instance);
      draw(instance, 1, false);
    }
    return api;
  }

  function keysFor(node) {
    if (Array.isArray(node)) return node.flatMap(keysFor);
    if (node && typeof node !== 'string') {
      for (const [key, instance] of instances) if (instance.element === node) return [key];
      return [];
    }
    const key = String(node || '').replace(/-engine$/, '');
    if (key === 'understand') return ['extract', 'detect'];
    if (key === 'protect') return ['redact', 'verify'];
    if (key === 'gateway') return ['network'];
    if (key === 'shared-chat') return ['shares'];
    return instances.has(key) ? [key] : [];
  }

  function render({node, time = 0, duration = 18, reduced = false, overview = false, playing = true} = {}) {
    const keys = node == null ? [...instances.keys()] : keysFor(node);
    if (overview || reduced) {
      for (const key of keys) if (instances.has(key)) draw(instances.get(key), 1, false);
      return;
    }
    const progress = clamp(Number(time) / Math.max(.05, Number(duration) || 18));
    for (const key of keys) {
      const instance = instances.get(key);
      if (!instance) continue;
      let local = progress;
      if (keys.includes('redact') && keys.includes('verify')) local = key === 'redact' ? clamp(progress / .55) : clamp((progress - .46) / .54);
      if (keys.includes('extract') && keys.includes('detect')) local = key === 'extract' ? clamp(progress / .55) : clamp((progress - .40) / .60);
      draw(instance, local, Boolean(playing));
    }
  }

  const api = {mount, render};
  window.ComponentDemos = api;
}());
