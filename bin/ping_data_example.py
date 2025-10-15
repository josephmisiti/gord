import click
import pingintel_api

client = pingintel_api.PingDataAPIClient(environment="staging")


@click.command()
@click.option('--address', '-a', help='Address to enhance', required=True)
@click.option('--country', '-c', help='Country code for the address', required=False)
def cli(address, country):
    ret = client.enhance(address=address, country=country, sources=["PG", "PH"], include_raw_response=True)
    breakpoint()

    def prnt(source, v):
        latlng = (
            f"{round(v['latitude'], 6)},{round(v['longitude'], 6)}"
            if v.get('latitude') is not None and v.get('longitude') is not None
            else "n/a"
        )

        precconf = f"P={v.get('precision') or 'n/a'},C={v.get('confidence') or 'n/a'}"
        match_level = v.get('match_level')
        if match_level is None:
            match_level = precconf
        else:
            match_level = f"{match_level} ({precconf})"
        # match_level = precconf
        try:
            print(
                f"{source:<6} {latlng:<22} {match_level:<12} {v['city'] or '':<20} {v['state'] or '':<10} {v['postal_code'] or '':<10} {v['country'] or ''} {v['address_line_1'] or '':<10}"
            )
            if source == 'EG':
                r = v.get('raw_response', {}).get('candidates', [{}])[0].get('attributes', {})
                print(f"      ExType={r.get('ExInfo')} District={r.get('District')} Precinct={r.get('Precinct')}")
            elif source == 'GG':
                address_components = v.get('raw_response', {}).get('results', [])[0].get('address_components', [])
                things = []
                for ac in address_components:
                    if ac.get('long_name') != ac.get('short_name'):
                        things.append(f"{ac.get('long_name', '')} ({ac.get('short_name', '')})")
                    else:
                        things.append(f"{ac.get('long_name', '')}")  # ({ac.get('types', [])})")
                print(f"      Address Components: {', '.join(things)}")
            elif source == 'AZG':
                r = v.get('raw_response', {}).get('response', {}).get('results', [])
                if r:
                    r = r[0].get('address', {})
                    print(
                        f"      muni={r.get('municipality')} countrySecondarySubdivision={r.get('countrySecondarySubdivision')} countrySubdivision={r.get('countrySubdivision')}"
                    )
        except:
            raise  # print(f"{source:<6} {latlng:<22} {match_level:<12} idk")

    print(f"## Address: {address} ##")
    print()
    for source, v in sorted(ret['location_data'].items()):
        if source == 'GGB':
            continue
        if source.startswith('PG'):
            continue
        prnt(source, v)

    print()

    prnt('PG', ret['location_data']['PG'])
    prnt('PGB', ret['location_data']['PGB'])
    print()
    print()


if __name__ == '__main__':
    cli()

    # print_thingy("Half Moon Cay, BS", "BS")
    # print_thingy("Am Strande 3 d / e (Silo 4 and 5), 18055 Rostock, Germany", "DE")
    # print_thingy("465 Victoria Avenue, Chatswood NSW 2067, Australia", "AU")
    # print_thingy("DR Cruise Port, Ltd. (Amber Cove), Puerto Plata, 0, Dominican Republic", "DO")
    # print_thingy("Roatan Cruise Terminal (Mahogany Bay), Roatan, Honduras", "HN")
    # print_thingy("Grand Turks Cruise Terminal, Grand Turk, Turks & Caicos", "TC")
