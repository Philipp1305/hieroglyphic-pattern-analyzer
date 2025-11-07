------------------------------------------------------------------
-- T_IMAGES
------------------------------------------------------------------
create table T_IMAGES(
	id			integer	not null,
	img			bytea 	not null,
	file_name	text 	not null,
	mimetype	text 	not null,
	constraint	T_IMAGES_PK primary key (id)
);

create sequence T_IMAGES_SEQ
start with 1
increment by 1;

create or replace function SET_T_IMAGES_ID()
returns trigger as $$
begin
    new.id := nextval('T_IMAGES_SEQ');
    return new;
end;
$$ language plpgsql;

create or replace trigger T_IMAGES_TR
before insert on T_IMAGES
for each row
execute function SET_T_IMAGES_ID();

------------------------------------------------------------------
-- T_GARDINER_CODES
------------------------------------------------------------------
create table T_GARDINER_CODES(
	id			integer not null,
	code		text,
	unicode		text,
	constraint	T_GARDINER_CODES_PK primary key (id)
);

create sequence T_GARDINER_CODES_SEQ
start with 1
increment by 1;

create or replace function SET_T_GARDINER_CODES_ID()
returns trigger as $$
begin
    new.id := nextval('T_GARDINER_CODES_SEQ');
    return new;
end;
$$ language plpgsql;

create or replace trigger T_GARDINER_CODES_TR
before insert on T_GARDINER_CODES
for each row
execute function SET_T_GARDINER_CODES_ID();

------------------------------------------------------------------
-- T_HIEROGLYPHES
------------------------------------------------------------------
create table T_HIEROGLYPHES(
	id			integer not null,
	id_image	integer not null,
	id_gardiner integer,
	bbox_x 		double precision not null,
	bbox_y 		double precision not null,
	bbox_height double precision not null,
	bbox_width 	double precision not null,
	constraint 	T_HIEROGLYPHES_PK primary key (id, id_image),
	constraint	T_HIEROGLYPHES_FK_IMAGE foreign key (id_image) references T_IMAGES(id),
	constraint 	T_HIEROGLYPHES_FK_GARDINER foreign key (id_gardiner) references T_GARDINER_CODES(id)
);