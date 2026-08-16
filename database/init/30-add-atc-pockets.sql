-- ATC magazine pocket count per machine (Brother Speedio models vary: 21, 30, etc.)
-- Used to gap-fill ATCTL rows so empty-pocket views show all configured pockets.

ALTER TABLE machines ADD COLUMN IF NOT EXISTS atc_pockets INTEGER DEFAULT 21;

UPDATE machines SET atc_pockets = 21 WHERE atc_pockets IS NULL;
