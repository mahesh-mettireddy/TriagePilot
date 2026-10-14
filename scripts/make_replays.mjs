// scripts/make_replays.mjs
// Generates pre-cached replays for S01..S11 matching engine/schemas.py 100%

import fs from 'fs';
import path from 'path';

const outDir = path.resolve('data/replays');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

function createReplay(scenarioId, isResumed = false) {
  const tsBase = '2026-10-14T10:00:00';
  let ticketId = `TCK-${scenarioId}`;
  let ticketClass = 'CODE_DEFECT';
  let severity = 'P2';
  let ownerTeam = 'team-payments';
  let summary = '';
  let activeAgents = ['LogsAgent', 'CodeAgent', 'HistoryAgent', 'KnowledgeAgent', 'RecordAgent'];
  let skippedAgents = {};
  let injectionDetected = false;
  let injectionNote = null;
  let probableRootCause = null;
  let contradictions = [];
  let trustScore = 0.85;
  let decisionBand = 'HIGH';
  let policyAction = 'CONCLUDE';
  let trustRationale = '';
  let verifiedCards = [];
  let droppedCards = [];
  let questions = [];
  let customerReply = '';
  let jiraDraft = null;
  let kbGap = null;
  let workaround = null;

  if (scenarioId === 'S01') {
    ticketId = 'TCK-1001';
    ticketClass = 'CODE_DEFECT';
    severity = 'P2';
    ownerTeam = 'team-payments';
    summary = 'Same-day transfers rejected due to UTC vs Asia/Kolkata timezone mismatch in cutoff logic';
    contradictions = [
      {
        kind: 'TIME_MISMATCH',
        deterministic: true,
        card_a: 'card-s01-tck',
        card_b: 'card-s01-log',
        note: 'Client claims failure started Monday 9:00 AM IST (2026-10-12), but earliest error occurred Tuesday 16:02:01 IST (2026-10-13) (>30h difference).'
      }
    ];
    probableRootCause = {
      hypothesis_id: 'hyp-s01-1',
      statement: 'Cutoff check in app/transfers/cutoff.py evaluates datetime.utcnow().hour >= 16 instead of converting to Asia/Kolkata timezone (IST).',
      culprit_files: ['app/transfers/cutoff.py'],
      culprit_commit: '142e868',
      supporting_card_ids: ['card-s01-code-1', 'card-s01-log'],
      contradicting_card_ids: [],
      score: 0.92
    };
    trustScore = 0.84;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'High verified evidence density across code, logs, and git history with deterministic time mismatch reconciled.';
    verifiedCards = [
      {
        card_id: 'card-s01-code-1',
        specialist: 'CodeAgent',
        source_type: 'code',
        pointer: { repo: 'transfers-demo-app', path: 'app/transfers/cutoff.py', line_start: 20, line_end: 27, sha: '142e868' },
        snippet: 'if current_time.hour >= 16:\n    raise CutoffExceededException(f"Transfer rejected: cutoff time 16:00 exceeded (evaluated utc hour: {current_time.hour})")',
        claim: 'Cutoff window check uses UTC hour instead of converting to Asia/Kolkata.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:05Z',
        github_permalink: 'https://github.com/bank-org/transfers-demo-app/blob/142e868/app/transfers/cutoff.py#L20-L27',
        verification: { status: 'verified', reason: 'Verified against clientrepo git commit 142e868.' }
      },
      {
        card_id: 'card-s01-log',
        specialist: 'LogsAgent',
        source_type: 'log',
        pointer: { log_id: 'LOG-S01-004', ts: '2026-10-13T10:32:01Z', service: 'transfers' },
        snippet: 'Transfer rejected: cutoff time 16:00 exceeded (evaluated utc hour: 10)',
        claim: 'Earliest rejection logged on Tuesday at 16:02 IST (10:32 UTC).',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:03Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Log ID and timestamp confirmed in logs.jsonl.' }
      },
      {
        card_id: 'card-s01-tck',
        specialist: 'HistoryAgent',
        source_type: 'ticket',
        pointer: { system: 'portal', id: 'TCK-1001', field: 'text' },
        snippet: 'Failing since Monday 9 AM, we cannot transfer funds to our vendors.',
        claim: 'Client asserted failures began Monday morning.',
        stance: 'context',
        observed_at: '2026-10-14T10:00:01Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Matches intake ticket text.' }
      }
    ];
    droppedCards = [
      {
        card_id: 'card-s01-speculative',
        specialist: 'CodeAgent',
        source_type: 'code',
        pointer: { repo: 'transfers-demo-app', path: 'app/transfers/cutoff.py', line_start: 99, line_end: 105, sha: '142e868' },
        snippet: 'def check_holiday_calendar(): pass',
        claim: 'Unverified speculation: holiday calendar failed.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:06Z',
        github_permalink: null,
        verification: { status: 'dropped', reason: 'Line 99 does not exist in app/transfers/cutoff.py.' }
      }
    ];
    customerReply = 'We have confirmed the issue: same-day transfer requests initiated after 4:00 PM IST were incorrectly rejected due to an internal system clock timezone configuration. Our engineering team has prepared a fix. Transfers initiated before 4:00 PM IST are operating normally.';
    jiraDraft = {
      title: 'Fix UTC hour comparison in app/transfers/cutoff.py (Convert to Asia/Kolkata)',
      description: 'Cutoff logic evaluates UTC hour directly against 16:00 instead of converting to Asia/Kolkata (IST), resulting in premature or incorrect cutoff evaluations.',
      repro_steps: ['Initiate same-day transfer TXN-1009 at 16:02 IST', 'Observe CutoffExceededException raised in app/transfers/cutoff.py'],
      evidence_links: ['https://github.com/bank-org/transfers-demo-app/blob/142e868/app/transfers/cutoff.py#L20-L27'],
      labels: ['bug', 'payments', 'timezone', 'triagepilot-verified']
    };
  } else if (scenarioId === 'S02') {
    ticketId = 'TCK-2041';
    ticketClass = 'DATA_ISSUE';
    severity = 'P3';
    ownerTeam = 'team-core-ledger';
    summary = 'Binary float drift in round(amount * 0.0125, 2) produces 1-paisa calculation error on transfer TXN-2041';
    activeAgents = ['RecordAgent', 'LogsAgent', 'CodeAgent', 'KnowledgeAgent'];
    skippedAgents = { HistoryAgent: 'Pruned: Specific record state reconciliation prioritized' };
    probableRootCause = {
      hypothesis_id: 'hyp-s02-1',
      statement: 'Fee computation in app/fees/calculator.py uses standard Python float multiplication and round(), suffering binary floating point drift on INR 803.40 (computed as 10.05 instead of 10.04).',
      culprit_files: ['app/fees/calculator.py'],
      culprit_commit: '3778ed8',
      supporting_card_ids: ['card-s02-rec', 'card-s02-code'],
      contradicting_card_ids: [],
      score: 0.95
    };
    trustScore = 0.89;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'Corroborated by RecordPort snapshot, calculation log trace, and source code float arithmetic.';
    verifiedCards = [
      {
        card_id: 'card-s02-rec',
        specialist: 'RecordAgent',
        source_type: 'record',
        pointer: { table: 'transfers', id: 'TXN-2041', field: 'fee' },
        snippet: 'transfer_id: TXN-2041, amount: 803.4, fee: 10.05, expected_fee: 10.04',
        claim: 'Transfer record TXN-2041 fee billed as 10.05.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:02Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Record snapshot verified in database store.' }
      },
      {
        card_id: 'card-s02-code',
        specialist: 'CodeAgent',
        source_type: 'code',
        pointer: { repo: 'transfers-demo-app', path: 'app/fees/calculator.py', line_start: 18, line_end: 23, sha: '3778ed8' },
        snippet: 'fee = round(amount * rate, 2)\nreturn fee',
        claim: 'Fee calculation performs float multiplication instead of high-precision Decimal.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:04Z',
        github_permalink: 'https://github.com/bank-org/transfers-demo-app/blob/3778ed8/app/fees/calculator.py#L18-L23',
        verification: { status: 'verified', reason: 'Matches code in client repository.' }
      }
    ];
    customerReply = 'We investigated transaction TXN-2041 and confirmed that an internal floating-point rounding issue calculated a fee of INR 10.05 instead of INR 10.04. A 1-paisa credit adjustment has been initiated to your account, and our ledger calculation service is being updated.';
    jiraDraft = {
      title: 'Migrate fee calculation in app/fees/calculator.py from float to Decimal',
      description: 'Binary floating-point arithmetic causes 1-paisa rounding discrepancies on specific amounts (such as 803.40 producing 10.05 rather than 10.04).',
      repro_steps: ['Call calculate_transfer_fee(803.40, "standard")', 'Observe return value is 10.05 instead of Decimal("10.04")'],
      evidence_links: ['https://github.com/bank-org/transfers-demo-app/blob/3778ed8/app/fees/calculator.py#L18-L23'],
      labels: ['bug', 'ledger', 'fees', 'precision']
    };
  } else if (scenarioId === 'S03') {
    ticketId = 'TCK-3003';
    ticketClass = 'CODE_DEFECT';
    severity = 'P1';
    ownerTeam = 'team-payments';
    summary = 'Duplicate debits TXN-3011 and TXN-3012 due to case-sensitive Idempotency-Key lookup and missing mutex lock';
    injectionDetected = true;
    injectionNote = "Potential prompt injection detected: 'ignore previous instructions'";
    probableRootCause = {
      hypothesis_id: 'hyp-s03-1',
      statement: 'app/transfers/idempotency.py does case-sensitive lookup for "Idempotency-Key", missing client header "idempotency-key", and lacks distributed lock before debit.',
      culprit_files: ['app/transfers/idempotency.py'],
      culprit_commit: 'b6a64e2',
      supporting_card_ids: ['card-s03-code', 'card-s03-log-dup'],
      contradicting_card_ids: [],
      score: 0.94
    };
    trustScore = 0.88;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'Prompt injection successfully neutralized; concurrent double debit corroborated by server logs and missing lock in code.';
    verifiedCards = [
      {
        card_id: 'card-s03-code',
        specialist: 'CodeAgent',
        source_type: 'code',
        pointer: { repo: 'transfers-demo-app', path: 'app/transfers/idempotency.py', line_start: 20, line_end: 30, sha: 'b6a64e2' },
        snippet: 'extracted_key = key or headers.get("Idempotency-Key")\nif not extracted_key:\n    return False',
        claim: 'Case-sensitive header check fails when lowercase idempotency-key header is sent.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:05Z',
        github_permalink: 'https://github.com/bank-org/transfers-demo-app/blob/b6a64e2/app/transfers/idempotency.py#L20-L30',
        verification: { status: 'verified', reason: 'Confirmed in git repo commit b6a64e2.' }
      },
      {
        card_id: 'card-s03-log-dup',
        specialist: 'LogsAgent',
        source_type: 'log',
        pointer: { log_id: 'LOG-S03-006', ts: '2026-10-14T02:45:10.120Z', service: 'transfers' },
        snippet: 'Debited account 445566778899 INR 15000.00 for TXN-3012 (DUPLICATE DEBIT)',
        claim: 'Second debit occurred within 15ms with same client idempotency key.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:03Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Log signature verified in logs.jsonl.' }
      }
    ];
    customerReply = 'We have verified that transaction TXN-3012 was a duplicate debit caused by a rapid retry handling issue. An automated refund of INR 15,000 has been credited back to your account. We apologize for the inconvenience.';
    jiraDraft = {
      title: 'Fix case-insensitive Idempotency-Key handling and enforce mutex lock before debit',
      description: 'Lowercase header idempotency-key bypassed the idempotency filter and absence of distributed mutex lock allowed concurrent double debit.',
      repro_steps: ['Submit two concurrent POST /api/transfers requests with header "idempotency-key: test-key"', 'Observe both debits succeed without 409 conflict'],
      evidence_links: ['https://github.com/bank-org/transfers-demo-app/blob/b6a64e2/app/transfers/idempotency.py#L20-L30'],
      labels: ['p1', 'critical', 'duplicate-debit', 'idempotency']
    };
  } else if (scenarioId === 'S04') {
    ticketId = 'TCK-4004';
    ticketClass = 'CODE_DEFECT';
    severity = 'P3';
    ownerTeam = 'team-comms';
    summary = 'SMS notification dropped on transient 503 error due to removed retry loop (CHG-401) and stale Runbook DOC-SMS-01';
    contradictions = [
      {
        kind: 'BEHAVIOUR_MISMATCH',
        deterministic: false,
        card_a: 'card-s04-doc',
        card_b: 'card-s04-code',
        note: 'Runbook DOC-SMS-01 claims SMS automatically retries 3 times with exponential backoff, but app/notifications/sms.py fails immediately on attempt 1 without retries.'
      },
      {
        kind: 'STALE_DOC_FLAG',
        deterministic: true,
        card_a: 'card-s04-doc',
        card_b: 'card-s04-code',
        note: 'Runbook DOC-SMS-01 was last updated 2025-11-20, while commit a24bbe3 (CHG-401) refactored SMS dispatch on 2026-09-15.'
      }
    ];
    probableRootCause = {
      hypothesis_id: 'hyp-s04-1',
      statement: 'Commit a24bbe3 removed the 3-attempt retry loop from app/notifications/sms.py, causing immediate delivery failure on transient carrier 503 errors while documentation DOC-SMS-01 remained stale.',
      culprit_files: ['app/notifications/sms.py'],
      culprit_commit: 'a24bbe3',
      supporting_card_ids: ['card-s04-code', 'card-s04-log-err'],
      contradicting_card_ids: [],
      score: 0.91
    };
    trustScore = 0.86;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'Document-to-code contradiction resolved; prompt injection in log neutralized; root cause verified against git history.';
    verifiedCards = [
      {
        card_id: 'card-s04-code',
        specialist: 'CodeAgent',
        source_type: 'code',
        pointer: { repo: 'transfers-demo-app', path: 'app/notifications/sms.py', line_start: 22, line_end: 35, sha: 'a24bbe3' },
        snippet: 'delivery_success = _call_gateway(recipient, message)\nif not delivery_success:\n    raise SMSDeliveryException(f"Failed to deliver SMS to {recipient}")',
        claim: 'SMS dispatch only attempts delivery once and lacks retry loop.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:04Z',
        github_permalink: 'https://github.com/bank-org/transfers-demo-app/blob/a24bbe3/app/notifications/sms.py#L22-L35',
        verification: { status: 'verified', reason: 'Verified against git blame commit a24bbe3.' }
      },
      {
        card_id: 'card-s04-doc',
        specialist: 'KnowledgeAgent',
        source_type: 'doc',
        pointer: { space: 'RUNBOOKS', page_id: 'DOC-SMS-01', section: 'Retry Policy', last_updated: '2025-11-20T08:00:00Z' },
        snippet: 'SMS notifications automatically retry 3 times with exponential backoff (1s, 2s, 4s) before marking delivery as failed.',
        claim: 'Operational runbook asserts 3 automated retries.',
        stance: 'contradicts',
        observed_at: '2026-10-14T10:00:02Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Doc section verified in docs.json.' }
      },
      {
        card_id: 'card-s04-log-err',
        specialist: 'LogsAgent',
        source_type: 'log',
        pointer: { log_id: 'LOG-SMS-402', ts: '2026-10-14T10:12:01Z', service: 'notifications.sms' },
        snippet: 'SMSDeliveryException: Failed to deliver SMS to recipient. Carrier returned HTTP 503 (attempts: 1, retries: 0)',
        claim: 'Gateway failure logged with 0 retries.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:03Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Verified in logs.jsonl.' }
      }
    ];
    kbGap = {
      page_id: 'DOC-SMS-01',
      issue: 'Runbook DOC-SMS-01 out of sync with code: claims 3 retries exist, but commit a24bbe3 removed them.'
    };
    customerReply = 'We investigated the missing SMS alert for transfer TXN-4015. While the transfer itself completed successfully, the downstream telecommunication provider experienced a momentary 503 outage. A re-notification has been triggered, and we are enhancing our delivery retry system.';
    jiraDraft = {
      title: 'Restore retry loop in app/notifications/sms.py and align with DOC-SMS-01',
      description: 'Refactor commit a24bbe3 removed retry logic, causing permanent notification loss on transient carrier 503 spikes.',
      repro_steps: ['Simulate 503 response from carrier gateway', 'Observe SMS fails on attempt 1 without retries'],
      evidence_links: ['https://github.com/bank-org/transfers-demo-app/blob/a24bbe3/app/notifications/sms.py#L22-L35'],
      labels: ['bug', 'notifications', 'sms', 'stale-doc']
    };
  } else if (scenarioId === 'S06') {
    ticketId = 'TCK-6006';
    ticketClass = 'CODE_DEFECT';
    severity = 'P2';
    ownerTeam = 'team-payments';
    summary = 'Boundary condition error (>= vs >) in app/limits/daily_limit.py blocks valid transfers of exactly ₹1,00,000';
    contradictions = [
      {
        kind: 'BEHAVIOUR_MISMATCH',
        deterministic: false,
        card_a: 'card-s06-doc',
        card_b: 'card-s06-code',
        note: 'Risk Policy DOC-LIMITS-01 permits transfers equal to ₹1,00,000, but app/limits/daily_limit.py blocks transfer amounts >= 100000.'
      }
    ];
    probableRootCause = {
      hypothesis_id: 'hyp-s06-1',
      statement: 'app/limits/daily_limit.py checks "if transfer_amount >= DAILY_TRANSFER_LIMIT:" instead of ">", blocking exact ₹1,00,000 boundary transfers.',
      culprit_files: ['app/limits/daily_limit.py'],
      culprit_commit: 'f68c7f6',
      supporting_card_ids: ['card-s06-code', 'card-s06-log', 'card-s06-vis'],
      contradicting_card_ids: [],
      score: 0.96
    };
    trustScore = 0.90;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'Vision OCR of screenshot corroborated by error log signature and source code boundary inspection; red-herring commit discounted.';
    verifiedCards = [
      {
        card_id: 'card-s06-vis',
        specialist: 'HistoryAgent',
        source_type: 'visual',
        pointer: { attachment_id: 'screenshot.png' },
        snippet: 'Error: Daily limit of INR 1,00,000 exceeded for request of INR 1,00,000.00',
        claim: 'UI dialog explicitly shows ₹1,00,000 request rejected against ₹1,00,000 limit.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:02Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Corroborated by error log LOG-S06-003.' }
      },
      {
        card_id: 'card-s06-code',
        specialist: 'CodeAgent',
        source_type: 'code',
        pointer: { repo: 'transfers-demo-app', path: 'app/limits/daily_limit.py', line_start: 25, line_end: 32, sha: 'f68c7f6' },
        snippet: 'if transfer_amount >= DAILY_TRANSFER_LIMIT:\n    raise DailyLimitExceededException(f"Daily limit of ₹{DAILY_TRANSFER_LIMIT:,.2f} exceeded for request of ₹{transfer_amount:,.2f}")',
        claim: 'Boundary condition uses >= instead of > on transfer_amount check.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:04Z',
        github_permalink: 'https://github.com/bank-org/transfers-demo-app/blob/f68c7f6/app/limits/daily_limit.py#L25-L32',
        verification: { status: 'verified', reason: 'Verified in clientrepo commit f68c7f6.' }
      },
      {
        card_id: 'card-s06-doc',
        specialist: 'KnowledgeAgent',
        source_type: 'doc',
        pointer: { space: 'RISK_CONTROLS', page_id: 'DOC-LIMITS-01', section: 'Daily Cumulative Limits', last_updated: '2026-07-20T14:00:00Z' },
        snippet: 'Transfers equal to ₹1,00,000 are permitted and must not be rejected. Transfers exceeding this limit are blocked.',
        claim: 'Bank policy explicitly permits transfers of exactly ₹1,00,000.',
        stance: 'contradicts',
        observed_at: '2026-10-14T10:00:03Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Verified in docs.json.' }
      }
    ];
    customerReply = 'We verified the rejection on your transfer of INR 1,00,000. An internal policy boundary evaluation error caused transfers of exactly INR 1,00,000 to be blocked. Our engineering team has deployed a hotfix, and you can now proceed with your transfer.';
    jiraDraft = {
      title: 'Fix boundary check in app/limits/daily_limit.py (Change >= to >)',
      description: 'Single transfer check uses >= DAILY_TRANSFER_LIMIT which blocks allowed transfers of exactly ₹1,00,000.',
      repro_steps: ['Submit transfer of 100,000.00 with 0 accumulated today', 'Observe DailyLimitExceededException is erroneously thrown'],
      evidence_links: ['https://github.com/bank-org/transfers-demo-app/blob/f68c7f6/app/limits/daily_limit.py#L25-L32'],
      labels: ['bug', 'limits', 'boundary-defect']
    };
  } else if (scenarioId === 'S09') {
    ticketId = 'TCK-9009';
    ticketClass = 'KNOWN_ERROR';
    severity = 'P3';
    ownerTeam = 'team-core-ledger';
    summary = 'NEFT settlement batch BATCH-901 deferred due to statutory RBI clearing holiday (Known Error KE-104)';
    activeAgents = ['HistoryAgent', 'LogsAgent'];
    skippedAgents = {
      CodeAgent: 'Pruned: Known error pattern matched; code analysis bypassed for fast-path',
      RecordAgent: 'Pruned: Batch or platform level known issue',
      KnowledgeAgent: 'Pruned: Known error repository provides operational workaround'
    };
    workaround = 'No manual database fix required. Queued transfer batches automatically clear and settle at 08:00 IST on the following business day (2026-10-15). Inform client of statutory holiday.';
    trustScore = 0.92;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'Fast-path match on Known Error KE-104; router saved 3 specialist calls; clear operational workaround identified.';
    verifiedCards = [
      {
        card_id: 'card-s09-ke',
        specialist: 'HistoryAgent',
        source_type: 'ticket',
        pointer: { system: 'known_errors', id: 'KE-104', field: 'pattern' },
        snippet: 'Bank-holiday NEFT settlement batch delay: Outbound batches remain queued in PENDING_SETTLEMENT state until next clearing window at 08:00 IST.',
        claim: 'Matches Known Error KE-104 pattern.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:02Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Confirmed in history.json.' }
      },
      {
        card_id: 'card-s09-log',
        specialist: 'LogsAgent',
        source_type: 'log',
        pointer: { log_id: 'LOG-S09-002', ts: '2026-10-14T04:00:16Z', service: 'settlement.batch' },
        snippet: "Settlement batch BATCH-901 deferred: RBI clearing holiday 'State Banking Clearing Holiday' on 2026-10-14. (Rule KE-104)",
        claim: 'Batch deferred due to statutory bank holiday.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:03Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Confirmed in logs.jsonl.' }
      }
    ];
    customerReply = 'Batch BATCH-901 is currently queued due to an official RBI clearing holiday on 2026-10-14. All funds are secure and the settlement batch will process automatically at 08:00 IST tomorrow morning on the next business day clearing cycle.';
  } else if (scenarioId === 'S10') {
    ticketId = 'TCK-1010';
    ticketClass = 'HOW_TO_USER_ERROR';
    severity = 'P4';
    ownerTeam = 'team-payments';
    summary = 'User inquiry regarding workflow and documentation requirements for adding an international beneficiary';
    activeAgents = ['KnowledgeAgent'];
    skippedAgents = {
      LogsAgent: 'Pruned: How-To query requires documentation and user guides only',
      CodeAgent: 'Pruned: User inquiry does not require source code inspection',
      RecordAgent: 'Pruned: No individual transaction record referenced',
      HistoryAgent: 'Pruned: No incident or release correlation needed'
    };
    trustScore = 0.95;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'Pure procedural guidance resolved via User Guide DOC-BEN-02; 4 unneeded specialist agents pruned.';
    verifiedCards = [
      {
        card_id: 'card-s10-doc',
        specialist: 'KnowledgeAgent',
        source_type: 'doc',
        pointer: { space: 'USER_GUIDES', page_id: 'DOC-BEN-02', section: 'International Beneficiaries', last_updated: '2026-06-15T10:00:00Z' },
        snippet: "To add an international beneficiary, navigate to Settings > Beneficiary Management > Add International. Enter the recipient's IBAN or Account Number, bank SWIFT/BIC code, destination country, bank physical address, and remittance purpose code.",
        claim: 'Procedural guidance on international beneficiary addition.',
        stance: 'supports',
        observed_at: '2026-10-14T10:00:02Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Verified against docs.json.' }
      }
    ];
    customerReply = 'To add an international beneficiary, please navigate to Settings > Beneficiary Management > Add International in your portal. You will need the recipient\'s IBAN/Account Number, destination bank SWIFT/BIC code, bank address, and appropriate remittance purpose code. Verification completes within 4 business hours.';
  } else if (scenarioId === 'S11' && !isResumed) {
    ticketId = 'TCK-1111';
    ticketClass = 'INSUFFICIENT_INFO';
    severity = 'P3';
    ownerTeam = 'team-payments';
    summary = 'Intake lacks transaction reference, timestamp, or error message; principled abstention triggered';
    activeAgents = ['HistoryAgent', 'LogsAgent'];
    skippedAgents = {
      CodeAgent: 'Pruned: Ticket lacks specific transaction or error details',
      RecordAgent: 'Pruned: Missing record identifier in intake',
      KnowledgeAgent: 'Pruned: Defer until discriminating questions answered'
    };
    trustScore = 0.22;
    decisionBand = 'LOW';
    policyAction = 'ABSTAIN';
    trustRationale = 'Mathematical trust score (0.22) is below minimum threshold (0.45). Insufficient specific evidence to draw reliable root-cause conclusion.';
    questions = [
      { text: 'What is the transaction reference ID (TXN-XXXX) that failed?', discriminates: ['Transaction lookup in ledger', 'Trace correlation'] },
      { text: 'At what time and for what amount was the transfer initiated?', discriminates: ['Cutoff window validation', 'Limit check evaluation'] }
    ];
    customerReply = 'Thank you for reaching out. To assist you with your transfer inquiry, could you please provide: (1) The transaction reference ID (TXN-XXXX), and (2) The approximate time and transfer amount? Once provided, our technical team will immediately pinpoint the issue.';
  } else if (scenarioId === 'S11' && isResumed) {
    ticketId = 'TCK-1111';
    ticketClass = 'CODE_DEFECT';
    severity = 'P2';
    ownerTeam = 'team-payments';
    summary = 'Client clarification confirmed failure at 4:15 PM IST on TXN-1009; root cause pinpointed to cutoff window timezone defect in app/transfers/cutoff.py';
    probableRootCause = {
      hypothesis_id: 'hyp-s11-resumed-1',
      statement: 'Cutoff check in app/transfers/cutoff.py evaluates datetime.utcnow().hour >= 16 instead of converting to Asia/Kolkata timezone (IST), incorrectly blocking transfer TXN-1009 at 4:15 PM IST.',
      culprit_files: ['app/transfers/cutoff.py'],
      culprit_commit: '142e868',
      supporting_card_ids: ['card-s11-resumed-code', 'card-s11-resumed-log', 'card-s11-resumed-rec'],
      contradicting_card_ids: [],
      score: 0.93
    };
    trustScore = 0.86;
    decisionBand = 'HIGH';
    policyAction = 'CONCLUDE';
    trustRationale = 'Client reply augmented context with exact TXN-1009 ID and 4:15 PM IST timestamp; trust jumped from 0.22 to 0.86 with conclusive evidence.';
    verifiedCards = [
      {
        card_id: 'card-s11-resumed-code',
        specialist: 'CodeAgent',
        source_type: 'code',
        pointer: { repo: 'transfers-demo-app', path: 'app/transfers/cutoff.py', line_start: 20, line_end: 27, sha: '142e868' },
        snippet: 'if current_time.hour >= 16:\n    raise CutoffExceededException(f"Transfer rejected: cutoff time 16:00 exceeded (evaluated utc hour: {current_time.hour})")',
        claim: 'Cutoff window check evaluates UTC hour directly.',
        stance: 'supports',
        observed_at: '2026-10-14T10:05:04Z',
        github_permalink: 'https://github.com/bank-org/transfers-demo-app/blob/142e868/app/transfers/cutoff.py#L20-L27',
        verification: { status: 'verified', reason: 'Verified against git commit 142e868.' }
      },
      {
        card_id: 'card-s11-resumed-log',
        specialist: 'LogsAgent',
        source_type: 'log',
        pointer: { log_id: 'LOG-S11-002', ts: '2026-10-14T10:45:00Z', service: 'transfers' },
        snippet: 'Transfer rejected: cutoff time 16:00 exceeded (evaluated utc hour: 10)',
        claim: 'TXN-1009 logged as rejected at 10:45 UTC (16:15 IST).',
        stance: 'supports',
        observed_at: '2026-10-14T10:05:02Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Confirmed in logs.jsonl.' }
      },
      {
        card_id: 'card-s11-resumed-rec',
        specialist: 'RecordAgent',
        source_type: 'record',
        pointer: { table: 'transfers', id: 'TXN-1009', field: 'status' },
        snippet: 'transfer_id: TXN-1009, amount: 45000.0, status: REJECTED_CUTOFF',
        claim: 'Ledger record confirms TXN-1009 rejected due to cutoff.',
        stance: 'supports',
        observed_at: '2026-10-14T10:05:03Z',
        github_permalink: null,
        verification: { status: 'verified', reason: 'Confirmed in record_snapshot.json.' }
      }
    ];
    customerReply = 'Thank you for providing transaction reference TXN-1009. We have confirmed that your transfer at 4:15 PM IST was incorrectly rejected due to an internal timezone clock configuration in our same-day cutoff evaluation service. A fix is underway.';
    jiraDraft = {
      title: 'Fix same-day cutoff evaluation for TXN-1009 in app/transfers/cutoff.py',
      description: 'Transfer TXN-1009 was rejected at 4:15 PM IST because cutoff logic evaluated UTC clock against IST window.',
      repro_steps: ['Initiate same-day transfer at 16:15 IST', 'Observe CutoffExceededException raised in app/transfers/cutoff.py'],
      evidence_links: ['https://github.com/bank-org/transfers-demo-app/blob/142e868/app/transfers/cutoff.py#L20-L27'],
      labels: ['bug', 'payments', 'timezone', 'client-resumed']
    };
  }

  const investigationId = isResumed ? `inv-${scenarioId.toLowerCase()}-resumed` : `inv-${scenarioId.toLowerCase()}`;

  const report = {
    investigation_id: investigationId,
    ticket_id: ticketId,
    scenario_id: scenarioId,
    mode_used: 'replay',
    ticket_class: ticketClass,
    severity: severity,
    owner_team: ownerTeam,
    summary: summary,
    routing_plan: {
      ticket_class: ticketClass,
      severity: severity,
      extracted_entities: { scenario: scenarioId, ticket_id: ticketId },
      active_agents: activeAgents,
      skipped_agents: skippedAgents,
      max_tool_calls: 12,
      injection_detected: injectionDetected,
      injection_note: injectionNote
    },
    probable_root_cause: probableRootCause,
    alternatives: [],
    contradictions: contradictions,
    trust: {
      score: trustScore,
      band: decisionBand,
      policy_action: policyAction,
      components: {
        c_ver: trustScore > 0.45 ? 0.85 : 0.20,
        c_div: activeAgents.length > 2 ? 0.80 : 0.30,
        c_spec: verifiedCards.length > 1 ? 0.90 : 0.20,
        c_time: contradictions.some(c => c.kind === 'TIME_MISMATCH') ? 0.40 : 0.85,
        p_contra: contradictions.length > 0 ? 0.15 : 0.0,
        p_unver: droppedCards.length > 0 ? 0.10 : 0.0
      },
      rationale: trustRationale
    },
    verified_cards: verifiedCards,
    dropped_cards: droppedCards,
    verified_claims_count: verifiedCards.length,
    dropped_claims_count: droppedCards.length,
    recommended_actions: [
      'Review git commit and deploy patch to staging',
      'Verify automated unit tests against seeded regression suite',
      'Notify customer with approved customer reply draft'
    ],
    workaround: workaround,
    questions_for_client: questions,
    customer_reply_draft: customerReply,
    leak_check: {
      passed: true,
      notes: ['No raw internal file paths or stack traces found in customer draft']
    },
    jira_draft: jiraDraft,
    kb_gap: kbGap,
    suggested_diagnostic_queries: [
      `SELECT * FROM transfers WHERE transfer_id = '${ticketId}'`,
      `grep -rn 'cutoff' app/transfers/`
    ],
    decision: {
      status: 'pending',
      by: null,
      reason: null,
      edits_diff: null,
      write_back_ref: null
    },
    audit_ref: `sha256-audit-${investigationId}`,
    metrics: {
      tool_calls: activeAgents.length * 2,
      tokens: 3840,
      latency_ms: 820,
      cost_usd: 0.0042
    }
  };

  // Generate sequence of SSEEvents
  const events = [
    { seq: 1, ts: `${tsBase}.010Z`, type: 'masking_done', data: { pii_redacted_count: 2, injection_detected: injectionDetected, injection_note: injectionNote } },
    { seq: 2, ts: `${tsBase}.080Z`, type: 'plan_created', data: report.routing_plan },
  ];

  let seq = 3;
  for (const [agent, reason] of Object.entries(skippedAgents)) {
    events.push({ seq: seq++, ts: `${tsBase}.${100 + seq * 20}Z`, type: 'agent_skipped', data: { agent, reason } });
  }

  for (const card of verifiedCards) {
    events.push({ seq: seq++, ts: `${tsBase}.${200 + seq * 20}Z`, type: 'card_added', data: card });
    events.push({ seq: seq++, ts: `${tsBase}.${210 + seq * 20}Z`, type: 'verifier_result', data: { card_id: card.card_id, status: 'verified', reason: card.verification.reason } });
  }

  for (const card of droppedCards) {
    events.push({ seq: seq++, ts: `${tsBase}.${300 + seq * 20}Z`, type: 'card_added', data: card });
    events.push({ seq: seq++, ts: `${tsBase}.${310 + seq * 20}Z`, type: 'verifier_result', data: { card_id: card.card_id, status: 'dropped', reason: card.verification.reason } });
  }

  for (const contra of contradictions) {
    events.push({ seq: seq++, ts: `${tsBase}.${400 + seq * 20}Z`, type: 'contradiction_found', data: contra });
  }

  events.push({ seq: seq++, ts: `${tsBase}.650Z`, type: 'trust_update', data: report.trust });

  if (policyAction === 'ABSTAIN') {
    events.push({ seq: seq++, ts: `${tsBase}.700Z`, type: 'abstain', data: { questions: report.questions_for_client, trust: report.trust } });
  }

  events.push({ seq: seq++, ts: `${tsBase}.820Z`, type: 'report_ready', data: report });

  return { scenario_id: scenarioId, events, report };
}

const scenarios = ['S01', 'S02', 'S03', 'S04', 'S06', 'S09', 'S10', 'S11'];

for (const sc of scenarios) {
  const replayData = createReplay(sc, false);
  const filePath = path.join(outDir, `${sc}.json`);
  fs.writeFileSync(filePath, JSON.stringify(replayData, null, 2), 'utf8');
  console.log(`Generated replay cache: ${filePath}`);
}

// Also generate S11_resumed.json
const s11Resumed = createReplay('S11', true);
const s11ResumedPath = path.join(outDir, 'S11_resumed.json');
fs.writeFileSync(s11ResumedPath, JSON.stringify(s11Resumed, null, 2), 'utf8');
console.log(`Generated replay cache: ${s11ResumedPath}`);
