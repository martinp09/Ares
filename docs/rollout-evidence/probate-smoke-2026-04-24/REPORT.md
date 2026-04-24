# Harris Probate Last-Week Ares Smoke — 2026-04-24

Source: Harris County Clerk Probate search `https://www.cclerk.hctx.net/applications/websearch/CourtSearch_R.aspx?ID=5rboVfNJYS8mH7Mxhu4+EVBMtA0R5zGMtVhdi9+X6GKnkJ7YNZewGnsnMkJ4cOzrtUwLt7ddOrVz2bqL6EraWgtRT7OSe7uDS/LVKe2Sk8V9xSUMfwwa/d1VfHYX/EXz`

Raw rows: **202**

Keep-now rows: **113**

Ares `/lead-machine/probate/intake` status: **201**

Ares processed: **113**, bridged canonical leads: **113**

## Keep-now type counts

- PROBATE OF WILL (INDEPENDENT ADMINISTRATION): 72
- INDEPENDENT ADMINISTRATION: 29
- APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP: 8
- APP TO DETERMINE HEIRSHIP: 4

## Workflow observations

- Search results expose case, court, file date, status, type, subtype, and estate style. They do **not** expose executor/applicant/heir names in list view.
- Ares normalized keep-now rows, scored them, persisted probate lead records, and bridged keep-now rows into canonical leads.
- No HCAD candidates were supplied in this run, so property matching remains `unmatched` until HCAD enrichment runs.
- Executor/heir extraction needs the case detail/party/doc image step next.

## Keep-now leads

| Case | Date | Court | Type | Decedent / Estate | Executor/Applicant |
|---|---:|---:|---|---|---|
| 543625 | 04/17/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Patricia M. Julian | not in search results |
| 543630 | 04/17/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Jacquelyn D. Davis | not in search results |
| 543631 | 04/17/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Bernhard Mundt | not in search results |
| 543633 | 04/17/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Kevin James Anderholm | not in search results |
| 543636 | 04/17/2026 | 5 | INDEPENDENT ADMINISTRATION | Max Ellison Merrill | not in search results |
| 543637 | 04/17/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Diane L Lapidus | not in search results |
| 543638 | 04/17/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Robert Joseph Syma | not in search results |
| 543639 | 04/17/2026 | 5 | INDEPENDENT ADMINISTRATION | Michelle L. Estep | not in search results |
| 543643 | 04/17/2026 | 5 | INDEPENDENT ADMINISTRATION | Beverly Joan Cross | not in search results |
| 543644 | 04/17/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Victor Laddie Stanek | not in search results |
| 543646 | 04/17/2026 | 1 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Horace Edward Wicker | not in search results |
| 543647 | 04/17/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Robert Louis Bauer | not in search results |
| 543648 | 04/17/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Robert George Berry | not in search results |
| 543650 | 04/17/2026 | 1 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | David Mark Lemons | not in search results |
| 543651 | 04/17/2026 | 1 | INDEPENDENT ADMINISTRATION | Marlowe Heath Leggs | not in search results |
| 543652 | 04/17/2026 | 4 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Janet Marie Mcmahan | not in search results |
| 543653 | 04/17/2026 | 2 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Dorothy Jean Dawson | not in search results |
| 543657 | 04/17/2026 | 5 | INDEPENDENT ADMINISTRATION | Victor Manuel Borjas, Jr. | not in search results |
| 543658 | 04/17/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Adelita Alicia Duhig | not in search results |
| 543659 | 04/17/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Stewart Jonathan Guss | not in search results |
| 543662 | 04/17/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Vance Neathery, Jr. | not in search results |
| 543649 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Lester J. Edwards | not in search results |
| 543661 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Betty Gene Porter Anton | not in search results |
| 543663 | 04/20/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Augustus Thornburn White | not in search results |
| 543664 | 04/20/2026 | 5 | INDEPENDENT ADMINISTRATION | Troy Edward Caffey | not in search results |
| 543665 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Ethel M. Carroll | not in search results |
| 543666 | 04/20/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | John Horne, Jr. | not in search results |
| 543669 | 04/20/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Louis Wilson | not in search results |
| 543670 | 04/20/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Kathleen Beique | not in search results |
| 543671 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Barbara Ariel Sollock | not in search results |
| 543672 | 04/20/2026 | 3 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Cindy Seltzer | not in search results |
| 543673 | 04/20/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Kathleen Auer Wood | not in search results |
| 543674 | 04/20/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Steven J. Jozwiak | not in search results |
| 543675 | 04/20/2026 | 4 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Kathleen V. Mccullough | not in search results |
| 543676 | 04/20/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Marian V. Meyer | not in search results |
| 543677 | 04/20/2026 | 3 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Nicolas Quintanilla | not in search results |
| 543678 | 04/20/2026 | 1 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Tangie Renee Williams | not in search results |
| 543679 | 04/20/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Yvette Everett | not in search results |
| 543680 | 04/20/2026 | 2 | APP TO DETERMINE HEIRSHIP | Debra Ann Young | not in search results |
| 543683 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Elizabeth Hohlt Pecore | not in search results |
| 543687 | 04/20/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Debra Huack Blackshear | not in search results |
| 543689 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | John William Price | not in search results |
| 543690 | 04/20/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Michael L. Warneke | not in search results |
| 543691 | 04/20/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Francisco Javier Castro | not in search results |
| 543692 | 04/20/2026 | 4 | INDEPENDENT ADMINISTRATION | Kirk E. Blackmon | not in search results |
| 543693 | 04/20/2026 | 4 | INDEPENDENT ADMINISTRATION | Paula Beeson Chapa | not in search results |
| 543695 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Shirley Pugh Laymond | not in search results |
| 543697 | 04/20/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Daniel Russell Starr | not in search results |
| 543702 | 04/20/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Thomas F Hunt | not in search results |
| 543705 | 04/20/2026 | 1 | INDEPENDENT ADMINISTRATION | Dorris Lucille Knight | not in search results |
| 543708 | 04/20/2026 | 4 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Karen Renee Vieira | not in search results |
| 543715 | 04/20/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Bobbie L. Davis | not in search results |
| 543721 | 04/20/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Althea Rhodes Williams | not in search results |
| 543696 | 04/21/2026 | 4 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Prasad Athota | not in search results |
| 543703 | 04/21/2026 | 4 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Robbin Clark Dunnell | not in search results |
| 543704 | 04/21/2026 | 4 | INDEPENDENT ADMINISTRATION | Natalie Ann Price | not in search results |
| 543706 | 04/21/2026 | 5 | INDEPENDENT ADMINISTRATION | Vinh Van Nguyen | not in search results |
| 543709 | 04/21/2026 | 1 | INDEPENDENT ADMINISTRATION | Hilda Charles | not in search results |
| 543710 | 04/21/2026 | 1 | INDEPENDENT ADMINISTRATION | Brandown Owen Parker | not in search results |
| 543711 | 04/21/2026 | 4 | INDEPENDENT ADMINISTRATION | Alfred Pennington, Iii | not in search results |
| 543716 | 04/21/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Dag Gustav Heggelund | not in search results |
| 543722 | 04/21/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Syed Raza | not in search results |
| 543724 | 04/21/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Earl Swindle | not in search results |
| 543725 | 04/21/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Brenda Lee Anderson Helmer | not in search results |
| 543726 | 04/21/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Gene Clark Childs | not in search results |
| 543727 | 04/21/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | John Robert Gealy | not in search results |
| 543729 | 04/21/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Cynthia Gold Ballard | not in search results |
| 543730 | 04/21/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | James Leonard Ivins | not in search results |
| 543731 | 04/21/2026 | 5 | INDEPENDENT ADMINISTRATION | Andrew Douglas Johnson | not in search results |
| 543732 | 04/21/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Clara Lucille Storkson | not in search results |
| 543734 | 04/21/2026 | 5 | INDEPENDENT ADMINISTRATION | Ava Lavonne Vlahakis | not in search results |
| 525833-401 | 04/22/2026 | 2 | APP TO DETERMINE HEIRSHIP | Daniel R. Montoya | not in search results |
| 543735 | 04/22/2026 | 2 | INDEPENDENT ADMINISTRATION | Michael Joseph Pelosi, Sr. | not in search results |
| 543736 | 04/22/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Mary Catherine Cezeaux | not in search results |
| 543737 | 04/22/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Clifton Felix Landry, Jr. | not in search results |
| 543739 | 04/22/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Leona Annie Helfrich | not in search results |
| 543740 | 04/22/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Marcia Ellen Korn | not in search results |
| 543743 | 04/22/2026 | 4 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | John Allen Broussard, Sr. | not in search results |
| 543744 | 04/22/2026 | 1 | INDEPENDENT ADMINISTRATION | Warren Huey Rudd | not in search results |
| 543745 | 04/22/2026 | 3 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Lisa Ann Couch | not in search results |
| 543746 | 04/22/2026 | 4 | INDEPENDENT ADMINISTRATION | Barbara P. Legrange | not in search results |
| 543747 | 04/22/2026 | 5 | INDEPENDENT ADMINISTRATION | Leonard Gutierrez, Jr. | not in search results |
| 543748 | 04/22/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Thomas Eugene Purcell | not in search results |
| 543749 | 04/22/2026 | 2 | INDEPENDENT ADMINISTRATION | Brad Daniel Clarke, Jr. | not in search results |
| 543751 | 04/22/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Miriam Marie Hartman Baldwin | not in search results |
| 543754 | 04/22/2026 | 4 | INDEPENDENT ADMINISTRATION | Barbara Sue Mccommas | not in search results |
| 543755 | 04/22/2026 | 5 | INDEPENDENT ADMINISTRATION | Eyda Cecelia Brown | not in search results |
| 543756 | 04/22/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Bettye Bozman | not in search results |
| 543758 | 04/22/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Refugio Orlando Medina | not in search results |
| 543759 | 04/22/2026 | 3 | APP TO DETERMINE HEIRSHIP | Robert Lee Warren | not in search results |
| 543760 | 04/22/2026 | 2 | INDEPENDENT ADMINISTRATION | Rosalee C. Cohen | not in search results |
| 543764 | 04/22/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Moses Ernesto Mondragon Jr | not in search results |
| 543767 | 04/22/2026 | 5 | INDEPENDENT ADMINISTRATION | Louverdie Nolbert | not in search results |
| 543773 | 04/22/2026 | 2 | INDEPENDENT ADMINISTRATION | Rodolfo Juan Flores | not in search results |
| 543777 | 04/22/2026 | 4 | INDEPENDENT ADMINISTRATION | Richard Hendrickson | not in search results |
| 543779 | 04/22/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Catherine N Woods | not in search results |
| 543781 | 04/22/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Woods Delay Dixon | not in search results |
| 543783 | 04/22/2026 | 4 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Sally Jean Wight | not in search results |
| 543784 | 04/22/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Rural David Spriggs | not in search results |
| 543787 | 04/22/2026 | 3 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Hai Nam Tran | not in search results |
| 543788 | 04/22/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Lois Dean Peniche | not in search results |
| 543789 | 04/22/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Richard Allen Kline | not in search results |
| 543790 | 04/23/2026 | 1 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Nancy J. Royall | not in search results |
| 543792 | 04/23/2026 | 2 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Brenda Kliem Besch | not in search results |
| 543794 | 04/23/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Berl Gene White | not in search results |
| 543795 | 04/23/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Luis Felipe Carballo Gomez | not in search results |
| 543796 | 04/23/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Angelina Roman | not in search results |
| 543798 | 04/23/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Arthur L. Schechter | not in search results |
| 543801 | 04/23/2026 | 2 | APP TO DETERMINE HEIRSHIP | Gloria Lavaughn Tyler Harris | not in search results |
| 543803 | 04/23/2026 | 4 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Lenore Jessica Haynes | not in search results |
| 543805 | 04/23/2026 | 5 | PROBATE OF WILL (INDEPENDENT ADMINISTRATION) | Thomas Trigg Lupher | not in search results |
| 543807 | 04/23/2026 | 4 | INDEPENDENT ADMINISTRATION | Robert Clayton Swanson | not in search results |
| 543808 | 04/23/2026 | 5 | INDEPENDENT ADMINISTRATION | Betty Sue O'Neil Reynolds | not in search results |

## Priority case-detail enrichment smoke

A second pass followed the Harris County case-detail AJAX endpoint (`CourtCaseDetail.aspx?ID=...`) for 12 highest-priority heirship/title-friction cases. The list-view still does not expose parties; the detail endpoint does.

Ares enriched-priority simulation:

- Input priority cases: **12**
- Kept by Ares: **12**
- Bridged canonical leads: **12**
- Lead score range: **59.0–75.0**
- Applicant captured in raw payload: **12**
- Applicant mailing address mapped for current model: **11**
- Respondent/heir candidates exposed by detail rows: **2**

Evidence files added:

- `priority_case_detail_raw.json`
- `priority_keep_now_enriched.json`
- `ares_priority_case_detail_intake_summary.json`
- `ares_priority_probate_records.json`
- `ares_priority_canonical_leads.json`

### Priority enriched lead list

| Case | Type | Decedent | Applicant / executor clue | Applicant address | Respondent / heir candidates | Key clue | Ares score |
|---|---|---|---|---|---|---|---:|
| 543653 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Dorothy Jean Dawson | Chris Leslie Bolivar, Sr. | 7802 Chasewood Dr, Missouri City TX 77489 | — | 04/21/2026: Basic Personal - Out / Private - Charlotte Lavonne Bolivar Weatherby- for pick up | 75.0 |
| 543652 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Janet Marie Mcmahan | Patrick Kelly McMahan | 5073 N. Nelson Dr, Katy TX 77493 | — | 04/21/2026: Notice of Deposit of Funds for Potential Attorney Ad Litem; 04/20/2026: Proof of Heirship by Publication | 75.0 |
| 543650 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | David Mark Lemons | James Corwin Lemons | 6750 Shining Sumac Ave, Houston TX 77084 | — | 04/20/2026: Proof of Heirship by Publication | 75.0 |
| 543646 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Horace Edward Wicker | Randy Edward Wicker | 5810 Horse Prairie Dr., Katy TX 77449 | — | 04/21/2026: ADMINISTRATION (IND/ DEP) Posting | 75.0 |
| 543680 | APP TO DETERMINE HEIRSHIP | Debra Ann Young | Cinceria Johnson | 1918 Skipwood Dr, Missouri City TX 77489 | — | 04/21/2026: Order Approving/Denying Emergency Intervention - For Funeral and Burial Expenses; In the amount of $5,000.00; 04/20/2026: Case Initiated Application (OCA) - Emergency Intervention Application for Funeral and Burial Expenses | 75.0 |
| 543678 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Tangie Renee Williams | Brittany C Edwards | 1614 Royal Grantham Ct, Houston TX 77073 | Frederick L Phillips, Christopher Dewanye Mcfadden, Jordan Anthony Brown, Laporchea Michelle Mcfadden | 04/21/2026: Proof of Heirship by Publication; 04/20/2026: Notice of Deposit of Funds for Potential Attorney Ad Litem | 75.0 |
| 543677 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Nicolas Quintanilla | Candida Neptalia Quintanilla | 12047 Green Coral Drive, Houston TX 77044 | — | 04/20/2026: Case Initiated Application (OCA) - INADM-HRSHP; 09/16/2025; NO SERV. REQ. | 75.0 |
| 543672 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Cindy Seltzer | Megan Galindo | 13018 Scenic Ritter St, Hedwig TX 78152 | — | 04/22/2026: Notice of Deposit of Funds for Potential Attorney Ad Litem; 04/21/2026: Proof of Heirship by Publication | 75.0 |
| 543759 | APP TO DETERMINE HEIRSHIP | Robert Lee Warren | Timothy Bernard Wilson | 1514 Lake Buchanan Cr, Richmond TX 77406 | — | 04/22/2026: Case Initiated Application (OCA) - HRSHP; DOD: 8/27/1998; publ-dcr , rd : 4/27/26 | 75.0 |
| 543745 | APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP | Lisa Ann Couch | Lisa Ann Couch | — | — | 04/22/2026: Application to Determine Heirship - HRSHP; DOD: 3/21/24; PUBL-DCR RD: 5/11/27 | 59.0 |
| 525833-401 | APP TO DETERMINE HEIRSHIP | Daniel R. Montoya | Annette Montoya | 4044 Basswood Dr, Dickinson TX 77539 | Larence Montoya, Adam R Montoya, Maria Silva, Monica Heimlich | 04/22/2026: Case Initiated Application (OCA) - Original Application for Partition and Distribution of Heirs Property | 75.0 |
| 543801 | APP TO DETERMINE HEIRSHIP | Gloria Lavaughn Tyler Harris | Carlotta Marie Tyler | 3014 Bolt St, Houston TX 77051 | — | 04/23/2026: Notice of Deposit of Funds for Potential Attorney Ad Litem; 04/23/2026: Application to Appoint Aty or Gdn Ad Ltm (No Fee) - Motion to Appoint Attorney Ad Litem | 75.0 |

### Remaining gaps from this smoke

- HCAD/property matching was not run in this case-detail pass, so all priority leads remain `hcad_match_status=unmatched`.
- Ares preserves applicant/heir detail in `raw_payload`, but the core probate model still lacks first-class applicant/respondent columns. That is the next backend wire-up if these fields need Mission Control filtering, assignment, or campaign export without custom raw-payload parsing.
- Tax delinquency overlay still needs the HCAD match output first. No fake tax flag was injected.
