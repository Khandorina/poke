--
-- PostgreSQL database dump
--

-- Dumped from database version 14.2
-- Dumped by pg_dump version 14.2

-- Started on 2023-12-16 00:34:58

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 210 (class 1259 OID 16783)
-- Name: battle_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.battle_history (
    id integer NOT NULL,
    pokemon1 character varying(100),
    pokemon2 character varying(100),
    winner integer,
    rounds integer,
    date bigint,
    username character varying(255)
);


ALTER TABLE public.battle_history OWNER TO postgres;

--
-- TOC entry 209 (class 1259 OID 16782)
-- Name: battle_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.battle_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.battle_history_id_seq OWNER TO postgres;

--
-- TOC entry 3337 (class 0 OID 0)
-- Dependencies: 209
-- Name: battle_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.battle_history_id_seq OWNED BY public.battle_history.id;


--
-- TOC entry 212 (class 1259 OID 16790)
-- Name: pokemon_comments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pokemon_comments (
    id integer NOT NULL,
    pokemon_name character varying(255),
    rating integer DEFAULT 5,
    comment character varying(255)
);


ALTER TABLE public.pokemon_comments OWNER TO postgres;

--
-- TOC entry 211 (class 1259 OID 16789)
-- Name: pokemon_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pokemon_comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pokemon_comments_id_seq OWNER TO postgres;

--
-- TOC entry 3340 (class 0 OID 0)
-- Dependencies: 211
-- Name: pokemon_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pokemon_comments_id_seq OWNED BY public.pokemon_comments.id;


--
-- TOC entry 214 (class 1259 OID 16800)
-- Name: pokemon_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pokemon_users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password character varying(255),
    lostpasscode character varying(255)
);


ALTER TABLE public.pokemon_users OWNER TO postgres;

--
-- TOC entry 213 (class 1259 OID 16799)
-- Name: pokemon_users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pokemon_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pokemon_users_id_seq OWNER TO postgres;

--
-- TOC entry 3343 (class 0 OID 0)
-- Dependencies: 213
-- Name: pokemon_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pokemon_users_id_seq OWNED BY public.pokemon_users.id;


--
-- TOC entry 3174 (class 2604 OID 16786)
-- Name: battle_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.battle_history ALTER COLUMN id SET DEFAULT nextval('public.battle_history_id_seq'::regclass);


--
-- TOC entry 3175 (class 2604 OID 16793)
-- Name: pokemon_comments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pokemon_comments ALTER COLUMN id SET DEFAULT nextval('public.pokemon_comments_id_seq'::regclass);


--
-- TOC entry 3177 (class 2604 OID 16803)
-- Name: pokemon_users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pokemon_users ALTER COLUMN id SET DEFAULT nextval('public.pokemon_users_id_seq'::regclass);


--
-- TOC entry 3345 (class 0 OID 0)
-- Dependencies: 209
-- Name: battle_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.battle_history_id_seq', 116, true);


--
-- TOC entry 3346 (class 0 OID 0)
-- Dependencies: 211
-- Name: pokemon_comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.pokemon_comments_id_seq', 15, true);


--
-- TOC entry 3347 (class 0 OID 0)
-- Dependencies: 213
-- Name: pokemon_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.pokemon_users_id_seq', 13, true);


--
-- TOC entry 3179 (class 2606 OID 16788)
-- Name: battle_history battle_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.battle_history
    ADD CONSTRAINT battle_history_pkey PRIMARY KEY (id);


--
-- TOC entry 3183 (class 2606 OID 16819)
-- Name: pokemon_users email_const; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pokemon_users
    ADD CONSTRAINT email_const UNIQUE (email);


--
-- TOC entry 3181 (class 2606 OID 16798)
-- Name: pokemon_comments pokemon_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pokemon_comments
    ADD CONSTRAINT pokemon_comments_pkey PRIMARY KEY (id);


--
-- TOC entry 3185 (class 2606 OID 16807)
-- Name: pokemon_users pokemon_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pokemon_users
    ADD CONSTRAINT pokemon_users_pkey PRIMARY KEY (id);


--
-- TOC entry 3336 (class 0 OID 0)
-- Dependencies: 210
-- Name: TABLE battle_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.battle_history TO pokegrafana;


--
-- TOC entry 3338 (class 0 OID 0)
-- Dependencies: 209
-- Name: SEQUENCE battle_history_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.battle_history_id_seq TO pokegrafana;


--
-- TOC entry 3339 (class 0 OID 0)
-- Dependencies: 212
-- Name: TABLE pokemon_comments; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.pokemon_comments TO pokegrafana;


--
-- TOC entry 3341 (class 0 OID 0)
-- Dependencies: 211
-- Name: SEQUENCE pokemon_comments_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.pokemon_comments_id_seq TO pokegrafana;


--
-- TOC entry 3342 (class 0 OID 0)
-- Dependencies: 214
-- Name: TABLE pokemon_users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.pokemon_users TO pokegrafana;


--
-- TOC entry 3344 (class 0 OID 0)
-- Dependencies: 213
-- Name: SEQUENCE pokemon_users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.pokemon_users_id_seq TO pokegrafana;


-- Completed on 2023-12-16 00:34:59

--
-- PostgreSQL database dump complete
--

