CREATE TABLE requests (
  datetime timestamp with time zone,
  app text,
  instance text,
  client_ip inet,
  client_id integer,
  request_method text,
  request_path text,
  response_code integer,
  response_size integer,
  response_time integer,
  client_ua text
);
