# Bristow-Hall Monitor V2.1 -- governed series registry (vault-backed)
# Baselines (Eq.5/Eq.6 percentiles) come from data_archive/current_revised_and_spatial
# deep current-revised history. Current values come from the live service where a
# route genuinely matches the same measurement; otherwise the vault value stands.
# cls: log=Eq.1 | dif=Eq.2 | lev=Eq.3      d: +1 increase adverse, -1 decrease adverse
FAMILIES=["labor","output_income","production_trade","housing","credit_banks",
          "markets_funding","prices_purchasing_power","business_formation",
          "regional_industry_breadth","financial_conditions"]
FAMILY_LABEL={"labor":"Labor","output_income":"Output & income",
 "production_trade":"Production & trade","housing":"Housing","credit_banks":"Credit & banks",
 "markets_funding":"Markets & funding","prices_purchasing_power":"Prices & purchasing power",
 "business_formation":"Business formation & investment",
 "regional_industry_breadth":"Industry breadth","financial_conditions":"Financial conditions"}
# (vault_series, family, dependency, cls, d, label, live_series_or_None)
REG=[
 ("PAYEMS","labor","payroll","log",-1,"Nonfarm payrolls","bls_core_live.CES0000000001"),
 ("CE16OV","labor","household_emp","log",-1,"Civilian employment","bls_core_live.LNS12000000"),
 ("UNRATE","labor","unemployment","dif",+1,"Unemployment rate","bls_core_live.LNS14000000"),
 ("U6RATE","labor","unemployment","dif",+1,"U-6 underemployment",None),
 ("ICNSA","labor","claims","log",+1,"Initial claims (NSA)","DERIVED.DOL.INITIAL_CLAIMS_US"),
 ("CCSA","labor","continued_claims","log",+1,"Continued claims",None),
 ("IURSA","labor","insured_unemp","dif",+1,"Insured unemployment rate","DERIVED.DOL.INSURED_UNEMP_RATE_US"),
 ("AWHMAN","labor","hours","log",-1,"Manufacturing workweek",None),
 ("JTSJOL","labor","vacancies","log",-1,"Job openings","bls_core_live.JTS000000000000000JOL"),
 ("JTSQUR","labor","quits","dif",-1,"Quits rate",None),
 ("EMRATIO","labor","emp_pop","dif",-1,"Employment-population ratio",None),
 ("TEMPHELPS","labor","temp_help","log",-1,"Temporary help services",None),
 ("UEMPMEAN","labor","unemp_duration","dif",+1,"Mean unemployment duration",None),

 ("GDPC1","output_income","gdp","log",-1,"Real GDP",None),
 ("CMRMTSPL","output_income","real_sales","log",-1,"Real mfg & trade sales",None),
 ("DSPIC96","output_income","real_income","log",-1,"Real disposable income",None),
 ("W875RX1","output_income","income_ex_transfer","log",-1,"Real income ex transfers",None),
 ("PCEC96","output_income","real_consumption","log",-1,"Real consumption",None),
 ("RRSFS","output_income","real_retail","log",-1,"Real retail & food sales",None),
 ("WEI","output_income","weekly_activity","lev",-1,"Weekly Economic Index","WEI"),
 ("CFNAI","output_income","national_activity","lev",-1,"Chicago Fed activity index","CFNAI"),
 ("CFNAIMA3","output_income","national_activity","lev",-1,"CFNAI 3-month average","CFNAIMA3"),
 ("ADS_INDEX","output_income","ads","lev",-1,"ADS business conditions",None),

 ("INDPRO","production_trade","industrial_production","log",-1,"Industrial production",None),
 ("IPMANSICS","production_trade","ip_manufacturing","log",-1,"IP: manufacturing",None),
 ("TCU","production_trade","capacity_utilization","dif",-1,"Capacity utilization",None),
 ("CUMFNS","production_trade","capacity_mfg","dif",-1,"Capacity utilization: mfg",None),
 ("NEWORDER","production_trade","new_orders","log",-1,"Core capital goods orders",None),
 ("DGORDER","production_trade","durable_orders","log",-1,"Durable goods orders",None),
 ("ISRATIO","production_trade","inventory_sales","dif",+1,"Inventory-to-sales ratio",None),
 ("TRUCKD11","production_trade","trucking","log",-1,"Truck tonnage","TRUCKD11"),
 ("RAILFRTCARLOADSD11","production_trade","rail","log",-1,"Rail carloads",None),

 ("HOUST","housing","starts","log",-1,"Housing starts",None),
 ("PERMIT","housing","permits","log",-1,"Building permits",None),
 ("MSACSR","housing","months_supply","dif",+1,"New-home months' supply",None),
 ("MORTGAGE30US","housing","mortgage_rate","dif",+1,"30-year mortgage rate",None),
 ("_r_USSTHPI","housing","house_prices","log",-1,"FHFA house price index",None),
 ("_r_PRFI","housing","res_investment","log",-1,"Residential fixed investment",None),

 ("DRTSCILM","credit_banks","ci_standards","dif",+1,"Banks tightening C&I standards","FED.SLOOS.SUBLPDCILS_N.Q"),
 ("BUSLOANS","credit_banks","business_loans","log",-1,"Commercial & industrial loans",None),
 ("TOTBKCR","credit_banks","bank_credit","log",-1,"Total bank credit",None),
 ("CCLACBW027SBOG","credit_banks","consumer_loans","log",-1,"Consumer loans at banks",None),
 ("TOTALSL","credit_banks","consumer_credit","log",-1,"Consumer credit outstanding",None),
 ("CMDEBT","credit_banks","household_debt","log",-1,"Household debt",None),
 ("NFCICREDIT","credit_banks","nfci_credit","lev",+1,"NFCI credit subindex","NFCICREDIT"),

 ("T10Y2Y","markets_funding","yield_curve","lev",-1,"10y-2y Treasury spread","DERIVED.CURVE.10Y_2Y"),
 ("T10Y3M","markets_funding","yield_curve_3m","lev",-1,"10y-3m Treasury spread",None),
 ("BAA10Y","markets_funding","credit_spread","lev",+1,"Baa spread over 10y",None),
 ("BAMLH0A0HYM2","markets_funding","high_yield_spread","lev",+1,"High-yield OAS",None),
 ("BAMLC0A0CM","markets_funding","ig_spread","lev",+1,"Investment-grade OAS",None),
 ("VIXCLS","markets_funding","volatility","lev",+1,"VIX",None),
 ("SP500","markets_funding","equity","log",-1,"S&P 500",None),
 ("NASDAQCOM","markets_funding","equity_nasdaq","log",-1,"Nasdaq Composite",None),
 ("CPFF","markets_funding","cp_funding","lev",+1,"3M CP minus fed funds","CPFF"),

 ("CPIAUCSL","prices_purchasing_power","consumer_prices","log",+1,"CPI-U","bls_core_live.CUSR0000SA0"),
 ("T5YIFR","prices_purchasing_power","inflation_expectations","lev",+1,"5y5y forward inflation","T5YIFR"),
 ("M2REAL","prices_purchasing_power","real_money","log",-1,"Real M2","M2REAL"),
 ("GASREGW","prices_purchasing_power","gasoline","log",+1,"Retail gasoline price",None),
 ("UMCSENT","prices_purchasing_power","sentiment","lev",-1,"Consumer sentiment",None),

 ("GPDIC1","business_formation","investment","log",-1,"Real gross private investment",None),
 ("TOTALSA","business_formation","vehicle_sales","log",-1,"Total vehicle sales",None),
 ("IHLIDXUS","business_formation","job_postings","log",-1,"Indeed job postings",None),
 ("AMTMNO","business_formation","mfg_orders","log",-1,"Manufacturers' new orders",None),

 ("MANEMP","regional_industry_breadth","ind_manufacturing","log",-1,"Manufacturing payrolls",None),
 ("USCONS","regional_industry_breadth","ind_construction","log",-1,"Construction payrolls",None),
 ("USTRADE","regional_industry_breadth","ind_retail","log",-1,"Retail trade payrolls",None),
 ("USWTRADE","regional_industry_breadth","ind_wholesale","log",-1,"Wholesale trade payrolls",None),
 ("USTPU","regional_industry_breadth","ind_transport_util","log",-1,"Transport & utilities payrolls",None),
 ("USINFO","regional_industry_breadth","ind_information","log",-1,"Information payrolls",None),
 ("USFIRE","regional_industry_breadth","ind_financial","log",-1,"Financial activities payrolls",None),
 ("USPBS","regional_industry_breadth","ind_prof_business","log",-1,"Professional & business payrolls",None),
 ("USEHS","regional_industry_breadth","ind_education_health","log",-1,"Education & health payrolls",None),
 ("USLAH","regional_industry_breadth","ind_leisure","log",-1,"Leisure & hospitality payrolls",None),
 ("USMINE","regional_industry_breadth","ind_mining","log",-1,"Mining & logging payrolls",None),
 ("GACDFSA066MSFRBPHI","regional_industry_breadth","philly_survey","lev",-1,"Philadelphia Fed activity","PHILLY.MBOS.GAC"),

 ("NFCI","financial_conditions","nfci","lev",+1,"NFCI","NFCI"),
 ("ANFCI","financial_conditions","anfci","lev",+1,"Adjusted NFCI",None),
 ("NFCIRISK","financial_conditions","nfci_risk","lev",+1,"NFCI risk subindex","NFCIRISK"),
 ("NFCILEVERAGE","financial_conditions","nfci_leverage","lev",+1,"NFCI leverage subindex","NFCILEVERAGE"),
 ("NFCINONFINLEVERAGE","financial_conditions","nfci_nonfin_leverage","lev",+1,"NFCI nonfinancial leverage",None),
 ("STLFSI4","financial_conditions","stlfsi","lev",+1,"St. Louis Fed stress index","STLFSI4"),
 ("USEPUINDXD","financial_conditions","policy_uncertainty","lev",+1,"Economic policy uncertainty",None),
]
# EXCLUDED FROM CONSTRUCTION (recession labels / target-trained probabilities).
# Available only as external comparators on the Recessions and Track-record tabs.
COMPARATORS=["USREC","USRECD","comp_USREC","comp_USRECD","comp_USRECDM",
             "RECPROUSM156N","SAHMCURRENT","SAHMREALTIME","nyfed_recession_prob","anxious_index"]
