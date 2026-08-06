-- =====================================================================
-- ProcureFlow - Faz 2: Yeni kullanicida otomatik profil olusturma
--
-- Amac: Bir kullanici Supabase Auth ile kaydoldugunda (auth.users tablosuna
-- yeni satir eklendiginde), public.profiles tablosuna otomatik olarak bir
-- profil satiri ve varsayilan rol ('employee') olustur.
--
-- Kavram - TRIGGER: "su olay olunca sunu otomatik calistir" kuralidir.
-- Burada olay = auth.users tablosuna INSERT.
-- =====================================================================

-- Tetiklenince calisacak fonksiyon.
-- SECURITY DEFINER: fonksiyon, sahibinin (yuksek) yetkisiyle calisir; boylece
-- auth semasindaki bir olaydan public.profiles'a yazabilir.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id, full_name, role)
    values (
        new.id,
        -- Kayit sirasinda 'full_name' verildiyse onu, yoksa e-postayi kullan.
        coalesce(new.raw_user_meta_data ->> 'full_name', new.email),
        'employee' -- her yeni kullanici varsayilan olarak 'employee'
    )
    on conflict (id) do nothing; -- ayni profil varsa tekrar ekleme
    return new;
end;
$$;

-- Onceki bir tanim varsa temizle (migration'i tekrar calistirmayi guvenli kilar).
drop trigger if exists on_auth_user_created on auth.users;

-- Tetikleyiciyi kur: auth.users'a her yeni satir eklendikten SONRA calis.
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();
