import os
import xml.etree.ElementTree as ET

# Set input and output paths
input_file = os.path.expanduser('~/Desktop/xls_als/library.xml')
output_folder = os.path.expanduser('~/Desktop/xls_als/tracks')

# Create output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Parse the Rekordbox XML library file
tree = ET.parse(input_file)
root = tree.getroot()

# Find all tracks in the library
tracks = root.findall('./COLLECTION/TRACK')

# Process each track
for track in tracks:
    # Get track name and artist, and make them valid file names
    track_name = track.get('Name')
    artist = track.get('Artist')
    valid_track_name = "".join(c for c in track_name if c.isalnum() or c in (' ', '.', '_')).rstrip()
    valid_artist_name = "".join(c for c in artist if c.isalnum() or c in (' ', '.', '_')).rstrip()
    
    track_folder = os.path.join(output_folder, f'{valid_artist_name} - {valid_track_name}')
    
    # Create the track folder if it doesn't exist
    if not os.path.exists(track_folder):
        os.makedirs(track_folder)

    output_file = os.path.join(track_folder, f'{valid_artist_name} - {valid_track_name}.xml')

    # Create a new XML structure for the individual track
    new_root = ET.Element('DJ_PLAYLISTS', {'Version': '1.0.0'})
    new_collection = ET.SubElement(new_root, 'COLLECTION')
    new_collection.append(track)

    # Write the individual track to an XML file
    new_tree = ET.ElementTree(new_root)
    new_tree.write(output_file, encoding='UTF-8', xml_declaration=True)

print(f'Successfully split {len(tracks)} tracks into individual XML files in {output_folder}')