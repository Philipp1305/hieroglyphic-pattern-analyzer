from src.database.connect import connect

conn = connect()
cursor = conn.cursor()

# Create the occurrences table
cursor.execute("""
CREATE TABLE IF NOT EXISTS T_SUFFIXARRAY_OCCURENCES (
    id          integer not null,
    id_pattern  integer not null,
    glyph_ids   integer[] not null,
    constraint  T_SUFFIXARRAY_OCCURENCES_PK primary key (id),
    constraint  T_SUFFIXARRAY_OCCURENCES_FK foreign key (id_pattern) references T_SUFFIXARRAY_PATTERNS(id) on delete cascade
)
""")

# Create sequence
cursor.execute("""
CREATE SEQUENCE IF NOT EXISTS T_SUFFIXARRAY_OCCURENCES_SEQ
START WITH 1
INCREMENT BY 1
""")

# Create trigger function
cursor.execute("""
CREATE OR REPLACE FUNCTION SET_T_SUFFIXARRAY_OCCURENCES_ID()
RETURNS TRIGGER AS $$
BEGIN
    NEW.id := nextval('T_SUFFIXARRAY_OCCURENCES_SEQ');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
""")

# Create trigger
cursor.execute("""
CREATE OR REPLACE TRIGGER T_SUFFIXARRAY_OCCURENCES_TR
BEFORE INSERT ON T_SUFFIXARRAY_OCCURENCES
FOR EACH ROW
EXECUTE FUNCTION SET_T_SUFFIXARRAY_OCCURENCES_ID()
""")

conn.commit()
cursor.close()
conn.close()

print('T_SUFFIXARRAY_OCCURENCES table, sequence, trigger function, and trigger created successfully!')
