GET_TRACKS_FOR_MEDIA = """
       query getTracksForMedia($media_id: Int!) {
           tracksByMediaId(media_id: $media_id) {
               track_uuid
               max_concept
               start_frame_number
               end_frame_number
           }
       }
       """

GET_MEDIA_IN_JOB = """
query getMediaInJob($processing_job_name: String!, $media_name: String!) {
    mediaInJob(processing_job_name: $processing_job_name, media_name: $media_name) 
    {
        name
        uuid
    }
}
"""