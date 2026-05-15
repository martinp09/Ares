---
title: REI Multichannel Campaign System
type: concept
created: 2026-05-02
updated: 2026-05-02
tags: [real-estate, campaign, cold-email, direct-mail, sms, compliance, probate]
sources: [raw/playbooks/rei-multichannel-marketing-playbook-2026-05-02.md]
---

# REI Multichannel Campaign System

This playbook defines the operating system for Ares seller outreach across cold email, direct mail, and SMS.

## Channel jobs

- **Cold email:** speed/testing channel. Its job is to verify interest, start low-friction conversations, test messaging cheaply, and support direct mail familiarity.
- **Direct mail:** trust/persistence channel. It is the safest cold channel and should carry the credibility/process layer.
- **SMS:** consent/inbound channel only. Do not cold-text random homeowners. Use SMS for inbound speed-to-lead, appointment confirmation, post-conversation follow-up, and permissioned offer links.

## External vs internal message

Internal acquisition objective:

> Source distressed/off-market real estate at a discount.

Seller-facing message:

> Simple as-is sale, no repairs, no agents, flexible closing, no pressure, transparent offer.

For probate/inherited property, Ares should translate this into:

> A simple no-prep way to find out whether an inherited property has a practical as-is path — without repairs, cleanout, listing, showings, perfect paperwork, or solving every title/tax/heirship question before the first conversation.

## Campaign sequence

The strongest system is not blasting. It is:

1. Property-list segmentation.
2. Direct mail drop.
3. Timed cold email.
4. Inbound call/text capture.
5. Live qualification.
6. Offer.
7. Nurture.
8. Reactivation.

For probate, this means direct mail should often create the first trust touch, while email references the same property/letter and asks for a low-friction reply.

## Compliance rules Ares must encode

### Cold email

- CAN-SPAM applies to commercial messages.
- Use accurate headers/from info.
- Use non-deceptive subject lines.
- Include a physical postal address.
- Include a clean opt-out line.
- Suppress anyone who replies remove/no/stop across channels.
- Keep subject lines boring and accurate.

### SMS

- SMS is not cold-prospecting unless documented consent exists and counsel approves.
- Use SMS after inbound/opt-in, form consent, appointment scheduling, or post-conversation permission.
- Ares should treat SMS enrollment as gated by consent evidence.

### Direct mail

- No fake official notices.
- No fake government language.
- No foreclosure-rescue language.
- Track with unique phone, PURL/landing page, QR/UTM, mail piece ID, and CRM matchback.

## Probate-specific translation

Probate/inherited outreach is high sensitivity. Avoid courthouse-vulture language.

Do not lead with:

- probate
- distressed
- delinquent
- behind on taxes
- urgent
- final notice
- foreclosure help
- cash approved

Lead with:

- reaching out about `{{property_address}}`
- inherited property / family property only where appropriate
- as-is option
- no repairs
- no cleanout
- no listing/showings
- flexible timing
- if keeping it is the plan, no problem
- if wrong person, Martin will close his notes

## Cadence doctrine

Short active sequence, then nurture.

Cold email should generally use 3-4 steps over ~14 days, then shift to 30-45 day nurture. Direct-mail-supported campaigns should use the mail piece as a trust anchor and email during/after the expected mail arrival window.

Ares default probate cadence:

- Day 0: direct mail letter.
- Day 5: email referencing the letter/property.
- Day 9: email with no-prep/as-is review angle.
- Day 15: email with convenience/clarity angle.
- Day 21-30: second mail piece.
- Day 25: close-the-loop email.
- Day 45: nurture begins.

## Metrics

Track outcomes by property record, not channel silo:

- positive reply rate
- negative reply rate
- opt-out/suppression rate
- qualified seller lead rate
- appointment/call rate
- offer request rate
- contract rate
- close rate
- cost per qualified seller lead
- cost per contract
- revenue per 1,000 records
- direct mail response / matchback by segment and creative

Do not optimize for opens. Open tracking can hurt deliverability and is not the business goal.

## Ares implementation rule

Every campaign asset should preserve:

- source segment
- property identity
- mail round and drop date
- mail creative ID
- email campaign ID
- last contact date
- last response
- channel-specific opt-out status
- global do-not-contact status
- consent evidence before SMS

The campaign generator should not create SMS cold-prospecting drafts unless the lead state contains consent/inbound evidence.

## Related

- [[high-response-email-formula]]
- [[offer-code-rosetta-stone]]
- [[inherited-property-offer-architecture]]
- [[copy-hinge]]
